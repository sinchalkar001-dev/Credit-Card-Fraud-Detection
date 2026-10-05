// Behaviour shared by every page: header, theme, messages, entrances.
import { drawEngravings, observeReveals, reducedMotion } from './motion.js';

const root = document.documentElement;

const TOAST_LIFE = { success: 5000, info: 5000, warning: 7000 };  // errors stay until dismissed

function initHeader() {
  const header = document.querySelector('[data-header]');
  if (!header) return;

  const markScrolled = () => header.toggleAttribute('data-scrolled', window.scrollY > 4);
  markScrolled();
  window.addEventListener('scroll', markScrolled, { passive: true });

  const toggle = header.querySelector('[data-menu-toggle]');
  if (!toggle) return;

  const setOpen = (open) => {
    header.toggleAttribute('data-menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Menu');
  };

  toggle.addEventListener('click', () => setOpen(!header.hasAttribute('data-menu-open')));

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && header.hasAttribute('data-menu-open')) {
      setOpen(false);
      toggle.focus();
    }
  });

  document.addEventListener('click', (event) => {
    if (header.hasAttribute('data-menu-open') && !header.contains(event.target)) setOpen(false);
  });

  // The panel only exists below the desktop breakpoint.
  window.matchMedia('(min-width: 60rem)').addEventListener('change', () => setOpen(false));
}

function initTheme() {
  const toggle = document.querySelector('[data-theme-toggle]');
  if (!toggle) return;

  const describe = () => {
    toggle.setAttribute('aria-label', root.dataset.theme === 'dark' ? 'Use light theme' : 'Use dark theme');
  };

  const apply = (theme, remember) => {
    root.dataset.theme = theme;
    describe();
    if (!remember) return;
    try {
      localStorage.setItem('theme', theme);
    } catch (error) {
      // Without storage the choice simply lasts for this page.
    }
  };

  toggle.hidden = false;
  describe();

  toggle.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';

    if (!document.startViewTransition || reducedMotion()) {
      apply(next, true);
      return;
    }

    // The new colours spread outwards from the button.
    const box = toggle.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    root.style.setProperty('--theme-x', `${x}px`);
    root.style.setProperty('--theme-y', `${y}px`);
    root.style.setProperty('--theme-r', `${radius}px`);

    root.classList.add('theme-switching');
    document.startViewTransition(() => apply(next, true))
      .finished.finally(() => root.classList.remove('theme-switching'));
  });

  // Follow the system until the person has chosen for themselves.
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
    let chosen = null;
    try {
      chosen = localStorage.getItem('theme');
    } catch (error) {
      chosen = null;
    }
    if (!chosen) apply(event.matches ? 'dark' : 'light', false);
  });
}

function dismissToast(toast) {
  if (toast.classList.contains('is-leaving')) return;
  toast.classList.add('is-leaving');
  // Leave after the exit animation, or straight away if it never runs.
  window.setTimeout(() => toast.remove(), reducedMotion() ? 0 : 200);
}

function initToast(toast) {
  const category = [...toast.classList].find((name) => name.startsWith('toast--'))?.slice(7) || 'info';
  const life = TOAST_LIFE[category];
  const close = toast.querySelector('[data-toast-close]');
  const timerBar = toast.querySelector('.toast__timer');

  if (close) {
    close.hidden = false;
    close.addEventListener('click', () => dismissToast(toast));
  }

  if (!life) {
    if (timerBar) timerBar.remove();
    return;
  }

  toast.style.setProperty('--toast-life', `${life}ms`);
  let remaining = life;
  let started = performance.now();
  let timer = window.setTimeout(() => dismissToast(toast), remaining);

  const pause = () => {
    window.clearTimeout(timer);
    remaining -= performance.now() - started;
    toast.setAttribute('data-paused', '');
  };

  const resume = () => {
    if (toast.matches(':hover') || toast.contains(document.activeElement)) return;
    started = performance.now();
    timer = window.setTimeout(() => dismissToast(toast), Math.max(remaining, 800));
    toast.removeAttribute('data-paused');
  };

  toast.addEventListener('pointerenter', pause);
  toast.addEventListener('pointerleave', resume);
  toast.addEventListener('focusin', pause);
  toast.addEventListener('focusout', resume);
}

function initToasts() {
  const toasts = [...document.querySelectorAll('[data-toast]')];
  toasts.forEach(initToast);

  // Messages rendered with the page are not announced on their own.
  const announcer = document.querySelector('[data-announcer]');
  if (announcer && toasts.length) {
    const text = toasts.map((toast) => toast.querySelector('.toast__message').textContent.trim()).join(' ');
    window.setTimeout(() => { announcer.textContent = text; }, 300);
  }
}

/** Say something to screen-reader users without moving focus. */
export function announce(message) {
  const announcer = document.querySelector('[data-announcer]');
  if (!announcer) return;
  announcer.textContent = '';
  window.setTimeout(() => { announcer.textContent = message; }, 50);
}

function initBusyForms() {
  document.querySelectorAll('form[data-busy]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      // Wait a tick so a page script can still cancel the submit.
      window.setTimeout(() => {
        if (event.defaultPrevented) return;
        const button = form.querySelector('[type="submit"]');
        if (button) button.setAttribute('aria-busy', 'true');
      });
    });
  });

  // Coming back with the browser's Back button restores the page as it was left.
  window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    document.querySelectorAll('[aria-busy="true"]').forEach((el) => el.removeAttribute('aria-busy'));
  });
}

initHeader();
initTheme();
initToasts();
initBusyForms();
observeReveals();
drawEngravings();

root.setAttribute('data-ready', '');
