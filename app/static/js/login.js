// Sign-in page: show or hide the password, and fill in the demo login.

const form = document.querySelector('[data-login-form]');

if (form) {
  const username = form.querySelector('#username');
  const password = form.querySelector('#password');
  const toggle = form.querySelector('[data-password-toggle]');

  if (toggle) {
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      const show = password.type === 'password';
      password.type = show ? 'text' : 'password';
      toggle.setAttribute('aria-pressed', String(show));
      toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
  }

  const fill = document.querySelector('[data-demo-fill]');
  if (fill) {
    fill.hidden = false;
    fill.addEventListener('click', () => {
      username.value = fill.dataset.username;
      password.value = fill.dataset.password;
      form.querySelector('[type="submit"]').focus();
    });
  }
}
