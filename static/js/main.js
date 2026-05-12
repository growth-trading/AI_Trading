/* AITrading — Main JS */

// Navbar scroll effect
const nav = document.getElementById('mainNav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 50);
  });
}

// IntersectionObserver — fade-in on scroll
const scrollEls = document.querySelectorAll('.animate-on-scroll');
if (scrollEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 100);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  scrollEls.forEach(el => obs.observe(el));
}

// Count-up animation for stats
function countUp(el, target, prefix, suffix, duration) {
  const isFloat = !Number.isInteger(target);
  const start = performance.now();
  const update = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = eased * target;
    el.textContent = prefix + (isFloat ? current.toFixed(1) : Math.floor(current).toLocaleString()) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

const statItems = document.querySelectorAll('.stat-item[data-count]');
if (statItems.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target.querySelector('.stat-number');
        const target = parseFloat(entry.target.dataset.count);
        const prefix = entry.target.dataset.prefix || '';
        const suffix = entry.target.dataset.suffix || '';
        countUp(el, target, prefix, suffix, 1800);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  statItems.forEach(el => obs.observe(el));
}

// Copy to clipboard
function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Đã sao chép!', 'success');
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('Đã sao chép!', 'success');
  });
}

// Toast notification
function showToast(message, type = 'success') {
  let container = document.querySelector('.messages-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'messages-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `alert-toast alert-toast-${type}`;
  const icon = type === 'success' ? 'check-circle-fill' : 'x-circle-fill';
  toast.innerHTML = `<i class="bi bi-${icon} me-2"></i>${message}
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// Auto-dismiss existing toasts
document.querySelectorAll('.alert-toast').forEach(el => {
  setTimeout(() => el.remove(), 5000);
});

// Nav coins live update via polling (dashboard)
function refreshCoins() {
  const el = document.getElementById('nav-coins-val');
  if (!el) return;
  fetch('/dashboard/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .catch(() => {});
}
