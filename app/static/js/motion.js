// Shared motion helpers. Timings mirror the tokens in css/tokens.css; anything
// that moves here checks prefers-reduced-motion first and, if it is set, goes
// straight to its final state.

const reduceQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

export const DURATION = { fast: 150, base: 240, slow: 420, slower: 720 };
const STAGGER_STEP = 50;
const STAGGER_CAP = 8;

export function reducedMotion() {
  return reduceQuery.matches;
}

export function easeOutExpo(t) {
  return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

export function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function nextFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

/**
 * Animate a number from `from` to `to`, calling onUpdate each frame.
 * Returns a function that cancels the animation where it stands.
 */
export function tween({ from = 0, to, duration = DURATION.slower, easing = easeOutExpo, onUpdate, onDone }) {
  if (reducedMotion() || duration <= 0 || from === to) {
    onUpdate(to);
    if (onDone) onDone();
    return () => {};
  }

  let frame = 0;
  const started = performance.now();

  const step = (now) => {
    const progress = Math.min(1, (now - started) / duration);
    onUpdate(from + (to - from) * easing(progress));
    if (progress < 1) {
      frame = requestAnimationFrame(step);
    } else if (onDone) {
      onDone();
    }
  };

  frame = requestAnimationFrame(step);
  return () => cancelAnimationFrame(frame);
}

const formatters = new Map();

export function formatNumber(value, decimals = 0) {
  if (!formatters.has(decimals)) {
    formatters.set(decimals, new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }));
  }
  return formatters.get(decimals).format(value);
}

const counts = new WeakMap();

/** Roll an element's number to a new value. A count already running is replaced. */
export function countTo(element, to, { from = 0, decimals = 0, duration, delay = 0 } = {}) {
  const running = counts.get(element);
  if (running) running();

  element.textContent = formatNumber(from, decimals);
  let cancel = () => {};
  const timer = window.setTimeout(() => {
    cancel = tween({
      from,
      to,
      duration,
      onUpdate: (value) => { element.textContent = formatNumber(value, decimals); },
    });
  }, reducedMotion() ? 0 : delay);

  counts.set(element, () => {
    window.clearTimeout(timer);
    cancel();
  });
}

/** Replay a CSS animation that is keyed to a class. */
export function restart(element, className) {
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
}

function startCounts(container, delay) {
  const targets = container.matches('[data-count]')
    ? [container]
    : container.querySelectorAll('[data-count]');

  targets.forEach((target) => {
    const to = Number(target.dataset.count);
    if (Number.isFinite(to)) {
      countTo(target, to, { decimals: Number(target.dataset.decimals || 0), delay: delay + 120 });
    }
  });
}

function show(element, delay) {
  element.style.setProperty('--reveal-delay', `${delay}ms`);
  element.classList.add('is-revealed');
  startCounts(element, delay);

  // Once it has arrived, hand the element's transitions back to its own styles.
  window.setTimeout(() => {
    element.removeAttribute('data-reveal');
    element.style.removeProperty('--reveal-delay');
  }, delay + DURATION.slow + 80);
}

/**
 * Reveal every [data-reveal] element as it enters the viewport. Elements that
 * enter together follow one another, top to bottom.
 */
export function observeReveals(root = document) {
  const targets = [...root.querySelectorAll('[data-reveal]')];
  if (!targets.length) return;

  if (reducedMotion() || !('IntersectionObserver' in window)) {
    targets.forEach((target) => show(target, 0));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top
        || a.boundingClientRect.left - b.boundingClientRect.left)
      .forEach((entry, index) => {
        observer.unobserve(entry.target);
        show(entry.target, Math.min(index, STAGGER_CAP) * STAGGER_STEP);
      });
  }, { rootMargin: '0px 0px -8% 0px' });

  targets.forEach((target) => observer.observe(target));
}

/** Draw the engraved lines of every guilloche marked data-draw. */
export function drawEngravings(root = document) {
  const engravings = root.querySelectorAll('.guilloche[data-draw]');
  if (!engravings.length) return;
  nextFrame().then(() => engravings.forEach((engraving) => engraving.classList.add('is-drawn')));
}
