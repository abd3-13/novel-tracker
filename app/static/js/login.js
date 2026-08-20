import { showNotification } from './notifi.js';
import { LOGIN_TEXT } from './library/config.js';

const form = document.getElementById('login-form');
const button = form.querySelector("button[type='submit']");

if (window.flashMessages) {
  window.flashMessages.forEach(([category, message]) => {
    showNotification(message, category);
  });
}

form.addEventListener('submit', async e => {
  e.preventDefault();

  button.disabled = true;
  button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${LOGIN_TEXT.signingIn}`;

  try {
    const response = await fetch(form.action || window.location.pathname, {
      method: 'POST',
      body: new FormData(form)
    });

    const data = await response.json();

    if (data.success) {
      window.location.href = data.redirect;
      return;
    }

    const username = form.username;
    const password = form.password;

    username.value = '';
    password.value = '';

    username.classList.add('is-invalid');
    password.classList.add('is-invalid');

    username.focus();
    form.username.addEventListener('input', () => {
      form.username.classList.remove('is-invalid');
    });
    form.password.addEventListener('input', () => {
      form.password.classList.remove('is-invalid');
    });
    showNotification(data.message, data.category, data.title);
  } catch (err) {
    console.error(err);

    showNotification(`${LOGIN_TEXT.loginFailed}\n\n ${err}`, 'error', LOGIN_TEXT.connectionError);
  } finally {
    button.disabled = false;
    button.innerHTML = LOGIN_TEXT.login;
  }
});
