function initSettings({ content }) {
  content.innerHTML = pageHeader('School Settings', 'Update the ZPPS Mamdapur name, logo and contact details.') +
    `<div id="settings-card">${card(skeletonBlock('h-72 w-full'))}</div>`;
  loadSettings();
}

async function loadSettings() {
  const mount = document.getElementById('settings-card');
  try {
    const settings = await api.get('/settings', null, { silent: true });
    mount.innerHTML = card(`
      <form id="school-settings-form" class="max-w-3xl space-y-5" enctype="multipart/form-data">
        <div class="flex items-center gap-4">
          ${settings.logo_url
            ? `<img src="${escapeHtml(settings.logo_url)}" alt="Current school logo" class="w-16 h-16 rounded-xl object-cover border border-line">`
            : `<div class="w-16 h-16 rounded-xl bg-primary-600 text-white flex items-center justify-center">${icon('school', 28)}</div>`}
          <div><p class="font-medium text-ink">School identity</p><p class="text-xs text-muted">This appears on the login page, public page and staff portal.</p></div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
          ${field({ name: 'school_name', label: 'Full school name', required: true, maxlength: 200, value: settings.school_name, className: 'sm:col-span-2' })}
          ${field({ name: 'school_short_name', label: 'Short name', required: true, maxlength: 80, value: settings.school_short_name })}
          ${field({ name: 'school_tagline', label: 'Tagline', required: true, maxlength: 200, value: settings.school_tagline })}
          ${field({ name: 'school_address', label: 'Address', maxlength: 300, value: settings.school_address, className: 'sm:col-span-2' })}
          ${field({ name: 'school_phone', label: 'Phone', maxlength: 30, value: settings.school_phone })}
          ${field({ name: 'school_email', label: 'Email', type: 'email', maxlength: 200, value: settings.school_email })}
          ${field({ name: 'logo', label: 'Change logo', type: 'file', accept: 'image/jpeg,image/png,image/webp,image/svg+xml', help: 'PNG, JPEG, WebP or SVG.' })}
        </div>
        <div class="flex justify-end"><button type="submit" class="${btnClass('primary')}">Save school settings</button></div>
      </form>`);
    const form = document.getElementById('school-settings-form');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const button = form.querySelector('button[type="submit"]');
      setBusy(button, true);
      try {
        await api.uploadPatch('/settings', new FormData(form));
        toast('School settings saved');
        await loadBranding();
        await loadSettings();
      } catch (error) {
        setBusy(button, false);
      }
    });
    refreshIcons();
  } catch (error) {
    showError(mount, error, loadSettings);
  }
}

const session = startPage('settings', 'School Settings');
if (session) initSettings(session);
