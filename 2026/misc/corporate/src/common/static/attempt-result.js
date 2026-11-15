'use strict';
(() => {
  const form = document.getElementById('compose');
  const dialog = document.getElementById('attempt-result');
  const status = document.getElementById('submit-status');
  const reference = document.getElementById('attempt-reference');
  const copyStatus = document.getElementById('attempt-copy-status');
  const progress = document.getElementById('submission-progress');
  const progressStatus = document.getElementById('submission-progress-status');
  let receipt = null,
    sending = false;
  let activeRequest = null;
  const canRetry = (result) =>
    ['busy', 'rate_limited'].includes(result?.code) &&
    Number.isFinite(result.retry_after) &&
    result.retry_after > 0;
  function preventLeaving(event) {
    event.preventDefault();
    event.returnValue = '';
  }
  function delay(milliseconds, signal) {
    return new Promise((resolve, reject) => {
      const stop = () => {
        clearTimeout(timer);
        reject(new DOMException('Submission interrupted', 'AbortError'));
      };
      const timer = setTimeout(() => {
        signal.removeEventListener('abort', stop);
        resolve();
      }, milliseconds);
      signal.addEventListener('abort', stop, { once: true });
      if (signal.aborted) stop();
    });
  }
  let uploadToken = null;
  async function uploadHeaders(signal) {
    if (!form.dataset.tokenUrl)
      return { 'X-CSRF-Token': document.getElementById('platform-csrf').value };
    // Renew before expiry; refreshing never changes the player's queue identity.
    if (!uploadToken || Date.now() >= uploadToken.refreshAt) {
      let response;
      try {
        response = await fetch(form.dataset.tokenUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRF-Token': document.getElementById('platform-csrf').value },
          cache: 'no-store',
          signal,
        });
      } catch {
        throw new Error('Could not renew upload access. Check your connection and try again.');
      }
      if (!response.ok)
        throw new Error('Platform access has expired. Reload the platform to sign in again.');
      const result = await response.json();
      uploadToken = {
        value: result.token,
        refreshAt: Date.now() + (result.expires_in - 60) * 1000,
      };
    }
    return { Authorization: `Bearer ${uploadToken.value}` };
  }
  async function waitForCapacity(capacity, signal) {
    while (true) {
      progressStatus.textContent = capacity.error;
      // Poll a small status response instead of repeatedly uploading attachments.
      await delay(
        Math.min(60, Math.max(1, capacity.retry_after)) * 1000 + Math.random() * 750,
        signal,
      );
      const response = await fetch(form.action + '/availability', {
        headers: { Accept: 'application/json', ...(await uploadHeaders(signal)) },
        credentials: form.dataset.tokenUrl ? 'omit' : 'same-origin',
        cache: 'no-store',
        signal,
      });
      if (!response.ok)
        throw new Error(
          'Could not check submission availability. Check your connection and platform access.',
        );
      capacity = await response.json();
      if (capacity.ready === true) return;
      if (!canRetry(capacity))
        throw new Error(
          capacity.error || 'Submissions are unavailable. Please contact the organizers.',
        );
    }
  }
  progress.addEventListener('cancel', (event) => event.preventDefault());
  function show(result) {
    receipt = result;
    document.getElementById('attempt-title').textContent =
      result.outcome === 'rejected' ? 'Rejected' : 'Email Delivered';
    dialog.dataset.outcome = result.outcome;
    document.getElementById('attempt-message').textContent = result.message;
    document.getElementById('attempt-message').hidden = !result.message;
    const rows = ['email', 'attachment', 'combined'].map((name) => {
      const row = document.createElement('tr');
      for (const value of [
        name === 'combined' ? 'Combined total' : name === 'email' ? 'Email' : 'Attachment',
        result.scores[name],
        result.thresholds[name],
      ]) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      row.dataset.triggered = String(result.triggered.includes(name));
      return row;
    });
    document.getElementById('attempt-scores').replaceChildren(...rows);
    const signals = result.signals.map((signal) => {
      const item = document.createElement('li');
      item.textContent =
        `${signal.label} (${signal.source}): +${signal.points}` +
        (signal.covered_by
          ? ` (${signal.rule_points} points covered by ${signal.covered_by})`
          : '');
      return item;
    });
    if (!signals.length) {
      const item = document.createElement('li');
      item.textContent = 'No screening signals. 0 points.';
      signals.push(item);
    }
    document.getElementById('attempt-signals').replaceChildren(...signals);
    reference.textContent = result.id;
    copyStatus.textContent = '';
    dialog.showModal();
  }
  window.corporateAsyncSubmission = true;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (sending || !window.corporateComposer.prepareSubmission()) return;
    sending = true;
    const payload = new FormData(form);
    if (form.dataset.tokenUrl) {
      payload.delete('csrf');
      payload.delete('upload_token');
      uploadToken = null;
    }
    const controller = new AbortController();
    activeRequest = controller;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    status.hidden = true;
    status.textContent = '';
    progressStatus.textContent = 'Uploading and screening your submission.';
    progress.showModal();
    window.addEventListener('beforeunload', preventLeaving);
    try {
      let result;
      while (true) {
        progressStatus.textContent = 'Uploading and screening your submission.';
        const response = await fetch(form.action, {
          method: 'POST',
          body: payload,
          headers: { Accept: 'application/json', ...(await uploadHeaders(controller.signal)) },
          credentials: form.dataset.tokenUrl ? 'omit' : 'same-origin',
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) {
          const error = response.headers.get('Content-Type')?.includes('application/json')
            ? await response.json()
            : null;
          // Only explicit pre-admission refusals may be retried safely.
          if (response.status === 429 && canRetry(error)) {
            await waitForCapacity(error, controller.signal);
            continue;
          }
          throw new Error(
            error?.error ||
              (response.status === 413
                ? 'Submission is too large.'
                : 'Submission failed. Check your platform access and try again.'),
          );
        }
        result = await response.json();
        break;
      }
      status.textContent = '';
      form.reset();
      const editor = document.getElementById('rich-body').contentDocument;
      if (editor?.body) editor.body.replaceChildren();
      progress.close();
      show(result);
    } catch (error) {
      status.hidden = false;
      status.textContent =
        error instanceof TypeError
          ? 'Connection lost. A result could not be received; your attempt may have been submitted. Do not retry automatically.'
          : error.message;
    } finally {
      progress.close();
      window.removeEventListener('beforeunload', preventLeaving);
      activeRequest = null;
      sending = false;
      button.disabled = false;
    }
  });
  reference.addEventListener('click', async () => {
    if (!receipt) return;
    try {
      await navigator.clipboard.writeText(receipt.id);
      copyStatus.textContent = 'Copied';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(reference);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copyStatus.textContent = 'Select and copy this reference.';
    }
  });
  document.getElementById('attempt-download').addEventListener('click', () => {
    if (!receipt) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(receipt, null, 2) + '\n'], { type: 'application/json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = `attempt-${receipt.id}-score.json`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  function clear() {
    receipt = null;
    dialog.removeAttribute('data-result');
    dialog.removeAttribute('data-outcome');
    for (const id of [
      'attempt-title',
      'attempt-message',
      'attempt-scores',
      'attempt-signals',
      'attempt-reference',
      'attempt-copy-status',
    ])
      document.getElementById(id).replaceChildren();
  }
  document.getElementById('attempt-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', clear);
  // Clear in-memory results before the browser can restore this page from bfcache.
  window.addEventListener('pagehide', () => {
    activeRequest?.abort();
    progress.close();
    dialog.close();
    clear();
  });
  if (dialog.dataset.result) {
    const result = JSON.parse(dialog.dataset.result);
    dialog.removeAttribute('data-result');
    show(result);
    document.getElementById('attempt-fallback')?.remove();
    history.replaceState(null, '', '/platform.aspx');
  }
})();
