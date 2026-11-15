const feed = document.querySelector('#feed');
const initialRealId = feed.dataset.initialRealId;
history.scrollRestoration = 'manual';
feed.scrollTop = 0;
let loading = false;
let paging = false;

const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#039;',
}[char]));

function card(real) {
  return `<article class="real" data-id="${real.real_id}">
    <div class="visual" style="--art:${real.art};--tilt:${real.tilt}deg"></div>
    <div class="real-content"><div class="copy">
      <div class="eyebrow">${escapeHtml(real.category)} / ${escapeHtml(real.age)}</div>
      <h1>${escapeHtml(real.title)}</h1>
      <p>${escapeHtml(real.content)}</p>
      <div class="creator">@${escapeHtml(real.creator)}</div>
    </div></div>
    <div class="actions">
      <button class="action like-btn" onpointerdown="likeDown(this)" onpointerup="likeUp(this)"><span class="icon">♡</span><span>${real.likes}</span></button>
      <button class="action" onclick="share(this)" aria-label="Share Real" title="Share Real"><span class="icon">➤</span><span>share</span></button>
    </div>
  </article>`;
}

async function likeDown(button) {
  const realId = button.closest('article').dataset.id;
  fetch(`/api/real/${encodeURIComponent(realId)}/like`, { method: 'POST' }).then(r => r.json()).then(d => {
    button.querySelector('span:last-child').textContent = d.likes;
  });
  button.querySelector('.icon').textContent = '\u2665';
  button.classList.add('active');
}

function likeUp(button) {
  const icon = button.querySelector('.icon');
  icon.textContent = '\u2661';
  button.classList.remove('active');
}

async function share(button) {
  await navigator.clipboard.writeText(window.location.href);
  const label = button.querySelector('span:last-child');
  label.textContent = 'copied';
  button.classList.add('active');
  setTimeout(() => {
    label.textContent = 'share';
    button.classList.remove('active');
  }, 1200);
}

async function loadReals(initial = false) {
  if (loading) return;
  loading = true;
  const query = new URLSearchParams();
  if (initial) query.set('initial', initialRealId);
  const response = await fetch(`/api/reals?${query}`);
  const reals = await response.json();
  if (initial) feed.replaceChildren();
  feed.insertAdjacentHTML('beforeend', reals.map(card).join(''));
  feed.querySelectorAll('.real:not([data-observed])').forEach((real) => {
    real.dataset.observed = 'true';
    observer.observe(real);
  });
  loading = false;
}

const observer = new IntersectionObserver((entries) => {
  const visible = entries.find((entry) => entry.isIntersecting);
  if (visible) {
    history.replaceState(null, '', `/real/${visible.target.dataset.id}`);
    if (visible.target === feed.lastElementChild) loadReals();
  }
}, { root: feed, threshold: 0.65 });

function currentIndex() {
  return Math.round(feed.scrollTop / feed.clientHeight);
}

function pageTo(index) {
  const next = Math.max(0, Math.min(index, feed.children.length - 1));
  const target = feed.children[next];
  if (!target) return;
  paging = true;
  feed.scrollTo({ top: target.offsetTop, behavior: 'smooth' });
  setTimeout(() => { paging = false; }, 500);
}

feed.addEventListener('wheel', (event) => {
  event.preventDefault();
  if (paging || Math.abs(event.deltaY) < 8) return;
  pageTo(currentIndex() + (event.deltaY > 0 ? 1 : -1));
}, { passive: false });

let touchStartY = 0;
feed.addEventListener('touchstart', (event) => { touchStartY = event.touches[0].clientY; }, { passive: true });
feed.addEventListener('touchend', (event) => {
  const distance = touchStartY - event.changedTouches[0].clientY;
  if (Math.abs(distance) > 40) pageTo(currentIndex() + (distance > 0 ? 1 : -1));
}, { passive: true });

window.addEventListener('keydown', (event) => {
  if (event.key === 'ArrowDown' || event.key === ' ') {
    event.preventDefault();
    pageTo(currentIndex() + 1);
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault();
    pageTo(currentIndex() - 1);
  }
});

loadReals(true).then(() => {
  document.querySelectorAll('.real').forEach((real) => observer.observe(real));
});

