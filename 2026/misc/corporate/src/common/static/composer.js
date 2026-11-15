'use strict';
const form = document.getElementById('compose');
const source = document.getElementById('body');
const frame = document.getElementById('rich-body');
let htmlMode = false,
  ready = false;
// The editor is a separate scriptless document. Raw email HTML never enters the
// platform DOM, and the editor's CSP blocks remote images, CSS URLs and forms.
frame.addEventListener('load', () => {
  if (ready) return;
  const doc = frame.contentDocument;
  if (!doc?.body) return;
  doc.body.contentEditable = 'true';
  doc.body.setAttribute('aria-label', 'Message body');
  doc.body.innerHTML = source.value;
  doc.addEventListener('click', (event) => {
    if (event.target.closest('a')) event.preventDefault();
  });
  ready = true;
  source.hidden = true;
  source.required = false;
  frame.hidden = false;
  document.getElementById('editor-toolbar').hidden = false;
});
frame.srcdoc = `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><style>body{font:15px/1.6 Arial,sans-serif;margin:16px;color:#111;min-height:240px;overflow-wrap:anywhere}body:focus{outline:none}a{color:inherit}img{max-width:100%}</style></head><body></body></html>`;
for (const button of document.querySelectorAll('[data-command]')) {
  button.addEventListener('mousedown', (event) => event.preventDefault());
  button.addEventListener('click', () => {
    if (ready && !htmlMode) {
      frame.contentWindow.focus();
      frame.contentDocument.execCommand(button.dataset.command, false);
    }
  });
}
document.getElementById('insert-link').addEventListener('click', () => {
  if (!ready || htmlMode) return;
  const address = prompt('Link URL');
  if (!address) return;
  try {
    const url = new URL(address);
    if (!['http:', 'https:', 'mailto:'].includes(url.protocol)) return;
  } catch {
    return;
  }
  frame.contentWindow.focus();
  frame.contentDocument.execCommand('createLink', false, address);
});
document.getElementById('editor-mode').addEventListener('click', (event) => {
  if (!ready) return;
  if (htmlMode) frame.contentDocument.body.innerHTML = source.value;
  else source.value = frame.contentDocument.body.innerHTML;
  htmlMode = !htmlMode;
  source.hidden = !htmlMode;
  frame.hidden = htmlMode;
  event.target.textContent = htmlMode ? 'Rich text' : 'HTML';
  event.target.setAttribute('aria-pressed', String(htmlMode));
  for (const button of document.querySelectorAll('[data-command], #insert-link'))
    button.disabled = htmlMode;
});
function prepareSubmission() {
  if (ready && !htmlMode) source.value = frame.contentDocument.body.innerHTML;
  if (!source.value.trim() || source.value.length > 100000) {
    alert(source.value.length > 100000 ? 'Message is too long.' : 'Enter a message body.');
    return false;
  }
  return true;
}
// The async sender calls this explicitly. Native posts use the same validation.
window.corporateComposer = { prepareSubmission };
form.addEventListener('submit', (event) => {
  if (!window.corporateAsyncSubmission && !prepareSubmission()) event.preventDefault();
});
