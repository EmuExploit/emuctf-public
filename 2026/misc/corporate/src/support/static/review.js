'use strict';
const $ = (id) => document.getElementById(id);
const root = document.querySelector('meta[name="review-root"]').content;
const csrf = document.querySelector('meta[name="review-csrf"]').content;
const labels = JSON.parse(document.getElementById('review-states').textContent);
const tabs = ['queue', 'rejected', 'accepted'];
const tabForState = (state) =>
  state === 'new' ? 'queue' : state === 'flag' ? 'accepted' : 'rejected';
let tab = 'queue',
  rows = [],
  selectedId = null,
  selected = null,
  nextCursor = null,
  loading = false,
  saving = false,
  savingComment = false,
  noticeTimer;
let prefix = '',
  searchTimer;
function updateTabs() {
  for (const name of tabs) $(name + '-tab').setAttribute('aria-pressed', String(tab === name));
}
function notice(message) {
  $('review-notice').textContent = message;
  $('review-notice').hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    $('review-notice').hidden = true;
  }, 3000);
}
async function api(path, options = {}) {
  const response = await fetch(root + path, { cache: 'no-store', ...options });
  if (response.status === 401) {
    location.assign(root + '/login');
    throw new Error('Sign in again');
  }
  if (!response.ok) throw new Error('Request failed');
  return response.json();
}
function tag(signal) {
  const item = document.createElement('span');
  item.className = 'mail-tag';
  const value =
    typeof signal === 'string'
      ? {
          label: signal,
          severity: ['YARA', 'SCAN ERROR', 'Extension', 'EMAIL', 'Size'].includes(signal)
            ? 'malicious'
            : 'informational',
        }
      : signal;
  item.textContent = value.label;
  item.dataset.severity = value.severity;
  item.title = `${value.severity.toUpperCase()}: ${value.label}`;
  return item;
}
function stateBadge(state) {
  const item = document.createElement('span');
  item.className = 'state-badge';
  item.dataset.state = state;
  item.textContent = labels[state] || state;
  item.title = 'State: ' + item.textContent;
  return item;
}
function renderDecision(mail) {
  const decision = mail.auto_rejection;
  $('recommendation').hidden = mail.state !== 'new' && !decision;
  $('recommendation').dataset.reject = String(Boolean(decision));
  $('recommendation-label').textContent = decision
    ? 'Auto-rejected: ' +
      labels[decision.state] +
      ' (' +
      decision.triggered.map((name) => name.toUpperCase()).join(' + ') +
      ')' +
      (mail.state !== decision.state ? ' · Current state: ' + labels[mail.state] : '')
    : 'Manual review';
  $('screening-score').textContent =
    `EMAIL ${mail.screening.scores.email} · ATTACHMENT ${mail.screening.scores.attachment} · TOTAL ${mail.screening.scores.combined}`;
}
function renderScoreChart(report) {
  // A point is always three pixels. Larger scores extend the ruler instead of
  // shrinking or normalizing earlier contributions to a percentage.
  const pixelsPerPoint = 3;
  const domain =
    Math.ceil(
      (Math.max(...Object.values(report.scores), ...Object.values(report.thresholds)) * 1.1 + 25) /
        25,
    ) * 25;
  const width = domain * pixelsPerPoint;
  const inner = document.createElement('div');
  inner.className = 'score-chart-inner';
  inner.style.width = `${width + 115}px`;
  const ruler = document.createElement('div');
  ruler.className = 'score-ruler';
  ruler.style.width = `${width}px`;
  const step = Math.max(25, Math.ceil(domain / 1250) * 25);
  for (let point = 0; point <= domain; point += step) {
    const tick = document.createElement('span');
    tick.textContent = point;
    tick.style.left = `${point * pixelsPerPoint}px`;
    ruler.append(tick);
  }
  inner.append(ruler);
  for (const name of ['email', 'attachment', 'combined']) {
    const row = document.createElement('div');
    row.className = 'score-row';
    const label = document.createElement('span');
    label.className = 'score-name';
    label.dataset.source = name;
    label.textContent = `${name.toUpperCase()} ${report.scores[name]}`;
    const track = document.createElement('div');
    track.className = 'score-track';
    track.style.width = `${width}px`;
    const fill = document.createElement('div');
    fill.className = 'score-fill';
    for (const source of name === 'combined' ? ['email', 'attachment'] : [name]) {
      const segment = document.createElement('span');
      segment.dataset.source = source;
      segment.style.width = `${report.scores[source] * pixelsPerPoint}px`;
      segment.title = `${source.toUpperCase()}: ${report.scores[source]} points`;
      fill.append(segment);
    }
    const threshold = document.createElement('span');
    threshold.className = 'score-threshold';
    threshold.style.left = `${report.thresholds[name] * pixelsPerPoint}px`;
    threshold.title = `${name.toUpperCase()} closing threshold: ${report.thresholds[name]}`;
    const marker = document.createElement('span');
    marker.textContent = `≥${report.thresholds[name]}`;
    threshold.append(marker);
    track.append(fill, threshold);
    row.append(label, track);
    inner.append(row);
  }
  $('score-chart').replaceChildren(inner);
  $('score-chart').setAttribute(
    'aria-label',
    ['email', 'attachment', 'combined']
      .map(
        (name) =>
          `${name}: ${report.scores[name]} points, closing threshold ${report.thresholds[name]}`,
      )
      .join('; '),
  );
}
function renderQueue() {
  const focused = document.activeElement.closest('.queue-entry')?.dataset.id;
  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.id = row.id;
    button.className = 'queue-entry' + (selectedId === row.id ? ' selected' : '');
    button.setAttribute('aria-pressed', String(selectedId === row.id));
    const head = document.createElement('span');
    head.className = 'queue-entry-head';
    const sender = document.createElement('span');
    sender.textContent = row.sender;
    const stamp = document.createElement('time');
    stamp.dateTime = row.created;
    stamp.textContent = new Date(row.created).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
    head.append(stateBadge(row.state), stamp);
    sender.className = 'queue-sender';
    const subject = document.createElement('strong');
    subject.className = 'queue-subject';
    subject.textContent = row.subject || '(no subject)';
    const tags = document.createElement('span');
    tags.className = 'tags';
    for (const signal of row.tags) tags.append(tag(signal));
    if (row.attachments)
      tags.append(
        tag({
          label: `${row.attachments} FILE${row.attachments === 1 ? '' : 'S'}`,
          severity: 'informational',
        }),
      );
    const reference = document.createElement('code');
    reference.className = 'queue-reference';
    reference.textContent = row.id;
    button.append(head, sender, subject, reference, tags);
    button.addEventListener('click', () => select(row.id));
    fragment.append(button);
  }
  if (!rows.length) {
    const empty = document.createElement('p');
    empty.className = 'queue-empty';
    empty.textContent = prefix ? 'No matching submissions' : 'No submissions';
    fragment.append(empty);
  }
  const scroll = $('queue-list').scrollTop;
  $('queue-list').replaceChildren(fragment);
  $('queue-list').scrollTop = scroll;
  if (focused) {
    for (const row of $('queue-list').children) {
      if (row.dataset.id === focused) row.focus({ preventScroll: true });
    }
  }
  $('load-more').hidden = !nextCursor;
}
async function refresh(reset = false, more = false) {
  if (!/^[0-9a-f]{0,32}$/.test(prefix)) {
    $('queue-status').textContent = 'Enter a hexadecimal reference prefix';
    return;
  }
  if (loading) return;
  const requestedTab = tab,
    requestedPrefix = prefix;
  loading = true;
  $('load-more').disabled = true;
  try {
    const query = new URLSearchParams({ tab: requestedTab });
    if (requestedPrefix) query.set('prefix', requestedPrefix);
    if (more && nextCursor) query.set('before', nextCursor);
    const result = await api('/api/submissions?' + query);
    if (requestedTab !== tab || requestedPrefix !== prefix) return;
    for (const name of tabs) $(name + '-count').textContent = result.counts[name];
    if (more) {
      const ids = new Set(rows.map((row) => row.id));
      rows.push(...result.items.filter((row) => !ids.has(row.id)));
      nextCursor = result.next_cursor;
    } else if (reset || rows.length <= 50 || !result.items.length) {
      rows = result.items;
      nextCursor = result.next_cursor;
    } else {
      // Keep already loaded older pages and the reader's selection during polling.
      const ids = new Set(result.items.map((row) => row.id));
      const boundary = result.items.at(-1);
      rows = [
        ...result.items,
        ...rows.filter(
          (row) =>
            !ids.has(row.id) &&
            (row.created < boundary.created ||
              (row.created === boundary.created && row.id < boundary.id)),
        ),
      ];
    }
    $('queue-status').textContent = prefix
      ? `${rows.length}${nextCursor ? '+' : ''} matching report${rows.length === 1 ? '' : 's'}`
      : 'Live';
    renderQueue();
    if (prefix && rows.length === 1 && !nextCursor && selectedId !== rows[0].id) select(rows[0].id);
  } catch {
    $('queue-status').textContent = 'Reconnecting…';
  } finally {
    loading = false;
    $('load-more').disabled = false;
    if (requestedTab !== tab || requestedPrefix !== prefix) refresh(true);
  }
}
function showEmpty() {
  selectedId = null;
  selected = null;
  $('submission').hidden = true;
  $('review-empty').hidden = false;
  $('mail-preview').removeAttribute('src');
  $('mail-source').textContent = '';
  renderQueue();
}
async function select(id) {
  selectedId = id;
  renderQueue();
  try {
    const mail = await api('/api/submissions/' + id);
    if (selectedId !== id) return;
    selected = mail;
    if (prefix) {
      tab = tabForState(mail.state);
      updateTabs();
    }
    $('mail-reference').textContent = mail.id;
    $('mail-subject').textContent = mail.subject;
    $('mail-from').textContent = mail.sender;
    $('mail-time').textContent = new Date(mail.created).toLocaleString();
    $('mail-ip').textContent = mail.client;
    $('mail-state').value = mail.state;
    $('save-status').textContent = '';
    $('review-comment').value = mail.comment;
    $('comment-status').textContent = '';
    $('download-email').href = mail.email_url;
    $('download-zip').href = mail.zip_url;
    $('download-zip').hidden = !mail.files.length;
    $('mail-tags').replaceChildren(...mail.tags.map((signal) => tag(signal)));
    if (!mail.tags.length)
      $('mail-tags').append(tag({ label: 'NO SIGNALS', severity: 'informational' }));
    const report = mail.screening;
    renderDecision(mail);
    renderScoreChart(report);
    const reasons = report.signals.map((signal) => {
      const row = document.createElement('li');
      row.dataset.source = signal.source;
      const label = document.createElement('strong');
      label.textContent = `${signal.label} +${signal.points}`;
      const text = document.createElement('span');
      text.textContent =
        (signal.covered_by ? ` (${signal.rule_points} covered by ${signal.covered_by})` : '') +
        ' — ' +
        signal.details.join('; ');
      row.append(label, text);
      return row;
    });
    $('mail-reasons').replaceChildren(...reasons);
    $('screening-details').open = false;
    $('mail-source').textContent = mail.body;
    $('mail-preview').src = mail.preview_url;
    $('mail-preview').hidden = false;
    $('mail-source').hidden = true;
    $('source-toggle').textContent = 'HTML source';
    $('source-toggle').setAttribute('aria-pressed', 'false');
    const files = document.createDocumentFragment();
    for (const file of mail.files) {
      const item = document.createElement('div');
      item.className = 'attachment';
      const link = document.createElement('a');
      link.className = 'attachment-link';
      link.href = file.download_url;
      link.textContent = `${file.name} ↓`;
      const size = document.createElement('span');
      size.className = 'file-size';
      size.textContent = `${(file.size / 1024).toFixed(1)} KiB`;
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = 'Scan details';
      const originalName = (file.original_name || file.name).replace(
        /[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]/g,
        (char) => '\\u' + char.codePointAt(0).toString(16).padStart(4, '0'),
      );
      const scan = document.createElement('pre');
      scan.textContent =
        `Original filename: ${originalName}\nfile: ${file.file_type?.description || 'Not identified'}\nMIME: ${file.file_type?.mime || 'unknown'}\nDeclared MIME: ${file.declared_mime || 'unknown'}\nSHA256: ${file.sha256}\nYARA: ${file.yara}` +
        (file.manual_review ? '\n' + file.manual_review : '');
      details.append(summary, scan);
      for (const member of file.yara_scan?.members || []) {
        const result = document.createElement('pre');
        result.textContent =
          `${member.name}: ${member.status}` + (member.detail ? `\n${member.detail}` : '');
        details.append(result);
      }
      item.append(link, size, details);
      files.append(item);
    }
    if (!mail.files.length) {
      const text = document.createElement('p');
      text.className = 'muted';
      text.textContent = 'None';
      files.append(text);
    }
    $('mail-files').replaceChildren(files);
    $('submission').hidden = false;
    $('review-empty').hidden = true;
  } catch {
    if (selectedId === id) {
      showEmpty();
      notice('Could not load submission');
    }
  }
}
$('reference-search').addEventListener('input', () => {
  prefix = $('reference-search').value.trim().toLowerCase();
  clearTimeout(searchTimer);
  rows = [];
  nextCursor = null;
  showEmpty();
  updateTabs();
  $('queue-status').textContent = 'Searching…';
  searchTimer = setTimeout(() => refresh(true), 200);
});
for (const name of tabs) {
  $(name + '-tab').addEventListener('click', () => {
    if (tab === name && !prefix) return;
    clearTimeout(searchTimer);
    prefix = '';
    $('reference-search').value = '';
    tab = name;
    rows = [];
    nextCursor = null;
    showEmpty();
    updateTabs();
    refresh(true);
  });
}
$('save-comment').addEventListener('click', async () => {
  if (!selectedId || savingComment) return;
  const id = selectedId,
    comment = $('review-comment').value;
  savingComment = true;
  $('save-comment').disabled = true;
  $('comment-status').textContent = 'Saving…';
  try {
    const result = await api('/api/submissions/' + id + '/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ comment }),
    });
    if (selectedId === id) {
      selected.comment = result.comment;
      $('comment-status').textContent =
        $('review-comment').value === result.comment ? 'Saved' : 'Unsaved';
    }
  } catch {
    if (selectedId === id) $('comment-status').textContent = 'Could not save';
  } finally {
    savingComment = false;
    $('save-comment').disabled = false;
  }
});
$('review-comment').addEventListener('input', () => {
  $('comment-status').textContent =
    selected && $('review-comment').value !== selected.comment ? 'Unsaved' : '';
});
$('load-more').addEventListener('click', () => refresh(false, true));
$('source-toggle').addEventListener('click', (event) => {
  const source = $('mail-source').hidden;
  $('mail-source').hidden = !source;
  $('mail-preview').hidden = source;
  event.target.textContent = source ? 'Preview' : 'HTML source';
  event.target.setAttribute('aria-pressed', String(source));
});
$('save-state').addEventListener('click', async () => {
  if (!selectedId || saving) return;
  const id = selectedId,
    state = $('mail-state').value;
  saving = true;
  $('save-state').disabled = true;
  try {
    const result = await api('/api/submissions/' + id + '/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ state }),
    });
    if (selectedId === id) {
      selected.state = result.state;
      selected.auto_rejection = result.auto_rejection;
      $('mail-state').value = result.state;
      renderDecision(selected);
      $('save-status').textContent =
        result.state === state ? 'Saved' : 'Auto-rejected: threshold reached';
    }
    if (!prefix && tabForState(result.state) !== tab) {
      rows = rows.filter((row) => row.id !== id);
      if (selectedId === id) {
        const next = rows[0]?.id;
        showEmpty();
        if (next) select(next);
      }
    }
    await refresh(true);
  } catch {
    notice('Could not save state');
  } finally {
    saving = false;
    $('save-state').disabled = false;
  }
});
async function poll() {
  await refresh();
  setTimeout(poll, 5000);
}
poll();
