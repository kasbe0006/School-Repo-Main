/*
 * page-login.js: the sign-in form.
 */

// Already logged in? Go straight to the app.
if (getToken() && getUser()) {
  window.location.replace(homePageFor(getUser().role));
}

const form = document.getElementById('login-form');
const errorBox = document.getElementById('login-error');
const button = document.getElementById('login-button');

loadBranding();

/** Show a message in the red error area above the form. */
function showLoginError(message) {
  errorBox.innerHTML = `${icon('circle-alert', 16, 'mt-px')}<span>${escapeHtml(message)}</span>`;
  errorBox.classList.remove('hidden');
  refreshIcons();
}

if (queryParam('expired')) showLoginError('Your session has expired. Please sign in again.');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorBox.classList.add('hidden');
  if (!validateForm(form)) return;

  setBusy(button, true, 'Signing in…');
  try {
    // silent: the error is shown in the form, not as a toast
    const result = await api.post('/auth/login', getFormValues(form), { silent: true });
    saveAuth(result);
    window.location.replace(homePageFor(result.role));
  } catch (error) {
    showLoginError(error.message || 'Login failed');
    setBusy(button, false);
    form.password.select();
  }
});
