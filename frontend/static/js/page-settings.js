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
      </form>
      <div class="max-w-3xl mt-8 pt-6 border-t border-line">
        <div class="flex items-center justify-between gap-3 mb-3">
          <div>
            <h2 class="font-semibold text-ink">School years</h2>
            <p class="text-xs text-muted mt-1">Choose which school year is active for timetable, attendance, results and billing.</p>
          </div>
          <button type="button" id="new-school-year" class="${btnClass('secondary', 'sm')}">${icon('plus', 14)} Add year</button>
        </div>
        <div id="school-year-list">${card(skeletonBlock('h-20 w-full'))}</div>
      </div>`);
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
    document.getElementById('new-school-year').addEventListener('click', openSchoolYearForm);
    loadSchoolYears();
    refreshIcons();
  } catch (error) {
    showError(mount, error, loadSettings);
  }

  async function loadSchoolYears() {
    const mount = document.getElementById('school-year-list');
    try {
      const data = await api.get('/semesters', { limit: 100, sort: 'start_date', order: 'desc' }, { silent: true });
      if (!data.items.length) {
        mount.innerHTML = `<p class="text-sm text-muted py-3">No school years created yet.</p>`;
        return;
      }
      mount.innerHTML = `<div class="divide-y divide-line border border-line rounded-lg overflow-hidden">
        ${data.items.map((year) => `<div class="flex items-center gap-3 px-3 py-3">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-ink">${escapeHtml(year.name)} ${year.is_active ? badge('published', 'Active') : ''}</p>
            <p class="text-xs text-muted mt-1">${escapeHtml(year.code)} · ${formatDate(year.start_date)} – ${formatDate(year.end_date)}</p>
          </div>
          ${year.is_active ? '' : `<button type="button" data-activate-year="${year.id}" class="${btnClass('secondary', 'sm')}">Make active</button>`}
        </div>`).join('')}
      </div>`;
      mount.querySelectorAll('[data-activate-year]').forEach((button) => {
        button.addEventListener('click', async () => {
          setBusy(button, true);
          try {
            await api.patch(`/semesters/${button.dataset.activateYear}/activate`);
            delete dataCache.semesters;
            delete dataCache['active-semester'];
            toast('Active school year changed');
            loadSchoolYears();
          } catch (error) {
            setBusy(button, false);
          }
        });
      });
      refreshIcons();
    } catch (error) {
      showError(mount, error, loadSchoolYears);
    }
  }

  function openSchoolYearForm() {
    formModal({
      title: 'Add school year',
      submitText: 'Create school year',
      fieldsHtml: `
        ${field({ name: 'name', label: 'School year name', required: true, maxlength: 60, placeholder: '2027-2028' })}
        ${field({ name: 'code', label: 'Short code', required: true, maxlength: 10, pattern: '[A-Z0-9-]{3,10}', placeholder: '2027-28' })}
        ${field({ name: 'start_date', label: 'Start date', type: 'date', required: true })}
        ${field({ name: 'end_date', label: 'End date', type: 'date', required: true })}
        ${field({ name: 'registration_start', label: 'Admission start', type: 'date', required: true })}
        ${field({ name: 'registration_end', label: 'Admission end', type: 'date', required: true })}`,
      onSubmit: (values) => api.post('/semesters', values),
      onSuccess: () => {
        delete dataCache.semesters;
        toast('School year created');
        loadSchoolYears();
      },
    });
  }
}

const session = startPage('settings', 'School Settings');
if (session) initSettings(session);
