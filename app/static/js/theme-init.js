// Runs in <head>, before the first paint, so the page never flashes the wrong
// theme or shows content that is about to be animated in.
(function () {
  var root = document.documentElement;
  var stored = null;

  try {
    stored = localStorage.getItem('theme');
  } catch (error) {
    // Storage can be blocked; the system preference still applies.
  }

  if (stored !== 'light' && stored !== 'dark') {
    stored = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  root.setAttribute('data-theme', stored);

  // html.js lets the stylesheet hold back anything the main script reveals.
  // If that script never arrives, give the page back in full.
  root.classList.add('js');
  window.setTimeout(function () {
    if (!root.hasAttribute('data-ready')) {
      root.classList.remove('js');
    }
  }, 3000);
})();
