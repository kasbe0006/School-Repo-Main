const CONTENT_KINDS = [
  { value: 'notice', label: 'Notice' },
  { value: 'activity', label: 'Activity / Event' },
  { value: 'gallery', label: 'Photo / Video' },
  { value: 'admission', label: 'Admission information' },
  { value: 'meal', label: 'Mid-day meal schedule' },
];

function initSchoolContent({ content, user }) {
  content.innerHTML = pageHeader(
    'Notices & Announcements',
    'Publish school notices, announcements, activities, gallery media, admission requirements and scholarship information.',
    user.role === 'admin'
      ? `<div class="flex flex-wrap gap-2">
          <button type="button" id="new-announcement" class="${btnClass('secondary')}">${icon('megaphone', 16)} New announcement</button>
          <button type="button" id="new-content" class="${btnClass('primary')}">${icon('plus', 16)} Add notice/content</button>
        </div>`
      : '',
  ) + `<div class="space-y-6">
    <section>
      <h2 class="text-sm font-semibold text-ink mb-3">Announcements</h2>
      <div id="announcement-list">${card(skeletonCards(2))}</div>
    </section>
    <section>
      <h2 class="text-sm font-semibold text-ink mb-3">School notices and content</h2>
      <div id="content-list">${card(skeletonCards(3))}</div>
    </section>
  </div>`;
  loadSchoolContent();
  loadAnnouncements();
  document.getElementById('new-content')?.addEventListener('click', openContentForm);
  document.getElementById('new-announcement')?.addEventListener('click', openAnnouncementForm);
}

function openContentEditForm(item) {
  const formId = 'edit-school-content-form';
  const modal = openModal({
    title: `Edit ${item.title}`,
    size: 'max-w-2xl',
    body: `<form id="${formId}" class="grid grid-cols-1 sm:grid-cols-2 gap-x-4" enctype="multipart/form-data">
      ${field({ name: 'kind', label: 'Content type', type: 'select', required: true, value: item.kind, options: CONTENT_KINDS })}
      ${field({ name: 'title', label: 'Title', required: true, maxlength: 200, value: item.title, className: 'sm:col-span-2' })}
      ${field({ name: 'description', label: 'Details', type: 'textarea', required: true, maxlength: 10000, value: item.description, className: 'sm:col-span-2' })}
      ${field({ name: 'event_date', label: 'Event date', type: 'date', value: item.event_date })}
      ${field({ name: 'event_end_date', label: 'Event end date', type: 'date', value: item.event_end_date })}
      ${field({ name: 'location', label: 'Location', maxlength: 200, value: item.location })}
      ${field({ name: 'documents_required', label: 'Documents needed', type: 'textarea', maxlength: 5000, value: item.documents_required, className: 'sm:col-span-2' })}
      ${field({ name: 'scholarship_info', label: 'Scholarship information', type: 'textarea', maxlength: 5000, value: item.scholarship_info, className: 'sm:col-span-2' })}
      ${field({ name: 'image', label: 'Replace photo', type: 'file', accept: 'image/jpeg,image/png,image/webp,image/gif' })}
      ${field({ name: 'video', label: 'Replace video', type: 'file', accept: 'video/mp4,video/webm,video/quicktime' })}
      ${field({ name: 'is_published', label: 'Published', type: 'checkbox', value: Boolean(item.is_published), className: 'sm:col-span-2' })}
    </form>`,
    footer: `<button type="button" data-cancel class="${btnClass('secondary')}">Cancel</button><button type="submit" form="${formId}" class="${btnClass('primary')}">Save changes</button>`,
  });
  modal.root.querySelector('[data-cancel]').addEventListener('click', modal.close);
  modal.root.querySelector('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    if (!data.get('is_published')) data.set('is_published', 'false');
    const submit = modal.root.querySelector('button[type="submit"]');
    setBusy(submit, true);
    try {
      await api.uploadPatch(`/school-content/${item.id}`, data);
      modal.close();
      toast('School content updated');
      loadSchoolContent();
    } catch (error) {
      setBusy(submit, false);
    }
  });
}

async function loadSchoolContent() {
  const mount = document.getElementById('content-list');
  try {
    const data = await api.get('/school-content', { limit: 100, sort: 'created_at', order: 'desc' });
    if (!data.items.length) {
      mount.innerHTML = card(emptyState({
        iconName: 'newspaper',
        title: 'No school content yet',
        subtitle: 'Add a notice, activity, gallery item or admission update.',
      }));
      return;
    }

    mount.innerHTML = `<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${data.items.map(contentCard).join('')}</div>`;
    mount.querySelectorAll('[data-delete-content]').forEach((button) => {
      button.addEventListener('click', async () => {
        if (!(await confirmDialog({ title: 'Delete this content?', message: 'This will remove the post and uploaded media.', confirmText: 'Delete' }))) return;
        await api.del(`/school-content/${button.dataset.deleteContent}`);
        toast('Content deleted');
        loadSchoolContent();
      });
    });
    mount.querySelectorAll('[data-edit-content]').forEach((button) => {
      button.addEventListener('click', () => openContentEditForm(data.items.find((item) => item.id === Number(button.dataset.editContent))));
    });
    refreshIcons();
  } catch (error) {
    showError(mount, error, loadSchoolContent);
  }
}

async function loadAnnouncements() {
  const mount = document.getElementById('announcement-list');
  try {
    const data = await api.get('/announcements', { limit: 100, sort: 'published_at', order: 'desc', include_expired: true });
    mount.innerHTML = data.items.length
      ? `<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${data.items.map(announcementCard).join('')}</div>`
      : card(emptyState({ iconName: 'megaphone', title: 'No announcements yet', subtitle: 'Create an announcement for school users.' }));
    refreshIcons();
    mount.querySelectorAll('[data-edit-announcement]').forEach((button) => {
      button.addEventListener('click', () => openAnnouncementForm(data.items.find((item) => item.id === Number(button.dataset.editAnnouncement))));
    });
    mount.querySelectorAll('[data-delete-announcement]').forEach((button) => {
      button.addEventListener('click', async () => {
        if (!(await confirmDialog({ title: 'Delete this announcement?', message: 'This cannot be undone.', confirmText: 'Delete' }))) return;
        await api.del(`/announcements/${button.dataset.deleteAnnouncement}`);
        toast('Announcement deleted');
        loadAnnouncements();
      });
    });
  } catch (error) {
    showError(mount, error, loadAnnouncements);
  }
}

function announcementCard(item) {
  const audience = [
    item.target_role ? `Role: ${titleCase(item.target_role)}` : '',
    item.target_department_code ? `Class group: ${item.target_department_code}` : '',
  ].filter(Boolean).join(' · ') || 'Everyone';
  return `<article class="bg-white rounded-xl border border-line shadow-sm p-5">
    <div class="flex items-start gap-3">
      <div class="w-9 h-9 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">${icon('megaphone', 16)}</div>
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="font-semibold text-ink">${escapeHtml(item.title)}</h3>
          ${item.is_expired ? badge('inactive', 'Expired') : badge('published', 'Published')}
        </div>
        ${getUser()?.role === 'admin' ? `<div class="flex gap-1 ml-auto">
          <button type="button" data-edit-announcement="${item.id}" class="${btnClass('ghost', 'icon-sm')}" title="Edit">${icon('pencil', 14)}</button>
          <button type="button" data-delete-announcement="${item.id}" class="${btnClass('ghost', 'icon-sm')} text-danger" title="Delete">${icon('trash-2', 14)}</button>
        </div>` : ''}
        <p class="text-sm text-slate-600 whitespace-pre-line mt-2">${escapeHtml(item.body)}</p>
        <p class="text-xs text-muted mt-3">${escapeHtml(audience)} · ${formatDateTime(item.published_at)}</p>
      </div>
    </div>
  </article>`;
}

async function openAnnouncementForm(announcement = null) {
  let departments = [];
  try {
    departments = await loadDepartments();
  } catch (error) {
    toast(error.message, 'error');
    return;
  }
  const modal = formModal({
    title: announcement ? 'Edit announcement' : 'New announcement',
    submitText: announcement ? 'Save announcement' : 'Publish announcement',
    size: 'max-w-2xl',
    fieldsHtml: `
      ${field({ name: 'title', label: 'Title', required: true, minlength: 3, maxlength: 150, value: announcement?.title })}
      ${field({ name: 'expires_on', label: 'Expires on', type: 'date', min: todayISO(), value: announcement?.expires_at?.slice(0, 10) })}
      ${field({ name: 'body', label: 'Announcement', type: 'textarea', required: true, minlength: 3, maxlength: 5000, value: announcement?.body, className: 'sm:col-span-2' })}
      ${field({ name: 'target_role', label: 'Audience role', type: 'select', emptyLabel: 'Everyone', value: announcement?.target_role, options: [
        { value: 'admin', label: 'Admins' }, { value: 'teacher', label: 'Teachers' },
        { value: 'student', label: 'Students' }, { value: 'accountant', label: 'Accountants' },
      ] })}
      ${field({ name: 'target_department_id', label: 'Class group', type: 'select', number: true, emptyLabel: 'All class groups', value: announcement?.target_department_id, options: toOptions(departments, (d) => d.code) })}`,
    onSubmit: (values) => announcement ? api.patch(`/announcements/${announcement.id}`, values) : api.post('/announcements', values),
    onSuccess: () => { toast(announcement ? 'Announcement updated' : 'Announcement published'); loadAnnouncements(); },
  });
  modal.form.classList.add('grid', 'grid-cols-1', 'sm:grid-cols-2', 'gap-x-4');
}

function contentCard(item) {
  const media = item.image_url
    ? `<img src="${escapeHtml(item.image_url)}" alt="" class="w-full h-44 object-cover rounded-lg mb-3">`
    : item.video_url
      ? `<video src="${escapeHtml(item.video_url)}" controls class="w-full h-44 object-cover rounded-lg mb-3"></video>`
      : '';
  const event = item.event_date ? `<p class="text-xs text-muted mt-2">${icon('calendar-days', 13)} ${escapeHtml(item.event_date)}${item.event_end_date ? ` – ${escapeHtml(item.event_end_date)}` : ''}${item.location ? ` · ${escapeHtml(item.location)}` : ''}</p>` : '';
  const extras = [
    item.documents_required ? `<p><strong>Documents:</strong> ${escapeHtml(item.documents_required)}</p>` : '',
    item.scholarship_info ? `<p><strong>Scholarships:</strong> ${escapeHtml(item.scholarship_info)}</p>` : '',
  ].join('');
  return `<article class="bg-white rounded-xl border border-line shadow-sm p-5">
    <div class="flex items-start justify-between gap-3 mb-3">
      <div><div class="flex gap-2 items-center">${badge(item.is_published ? 'published' : 'inactive', titleCase(item.kind))}${item.is_published ? '' : badge('inactive', 'Draft')}</div>
      <h3 class="font-semibold text-ink mt-2">${escapeHtml(item.title)}</h3></div>
      ${getUser()?.role === 'admin' ? `<div class="flex gap-1">
        <button type="button" data-edit-content="${item.id}" class="${btnClass('ghost', 'icon-sm')}" title="Edit">${icon('pencil', 14)}</button>
        <button type="button" data-delete-content="${item.id}" class="${btnClass('danger', 'icon-sm')}" title="Delete">${icon('trash-2', 14)}</button>
      </div>` : ''}
    </div>
    ${media}<p class="text-sm text-slate-600 whitespace-pre-line">${escapeHtml(item.description)}</p>${event}
    ${extras ? `<div class="text-xs text-slate-600 space-y-1 mt-3">${extras}</div>` : ''}
  </article>`;
}

function openContentForm() {
  const formId = 'school-content-form';
  const modal = openModal({
    title: 'Add school content',
    size: 'max-w-2xl',
    body: `<form id="${formId}" class="grid grid-cols-1 sm:grid-cols-2 gap-x-4" enctype="multipart/form-data">
      ${field({ name: 'kind', label: 'Content type', type: 'select', required: true, options: CONTENT_KINDS })}
      ${field({ name: 'title', label: 'Title', required: true, minlength: 3, maxlength: 200, className: 'sm:col-span-2' })}
      ${field({ name: 'description', label: 'Details', type: 'textarea', required: true, minlength: 3, maxlength: 10000, className: 'sm:col-span-2' })}
      ${field({ name: 'event_date', label: 'Event date', type: 'date' })}
      ${field({ name: 'event_end_date', label: 'Event end date', type: 'date' })}
      ${field({ name: 'location', label: 'Location', maxlength: 200 })}
      ${field({ name: 'documents_required', label: 'Documents needed', type: 'textarea', maxlength: 5000, className: 'sm:col-span-2', placeholder: 'Birth certificate, transfer certificate…' })}
      ${field({ name: 'scholarship_info', label: 'Scholarship information', type: 'textarea', maxlength: 5000, className: 'sm:col-span-2' })}
      ${field({ name: 'image', label: 'Photo', type: 'file', accept: 'image/jpeg,image/png,image/webp,image/gif' })}
      ${field({ name: 'video', label: 'Video', type: 'file', accept: 'video/mp4,video/webm,video/quicktime' })}
      ${field({ name: 'is_published', label: 'Publish now', type: 'checkbox', value: true, className: 'sm:col-span-2' })}
    </form>`,
    footer: `<button type="button" data-cancel class="${btnClass('secondary')}">Cancel</button><button type="submit" form="${formId}" class="${btnClass('primary')}">Publish</button>`,
  });
  modal.root.querySelector('[data-cancel]').addEventListener('click', modal.close);
  modal.root.querySelector('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    if (!data.get('is_published')) data.set('is_published', 'false');
    const submit = modal.root.querySelector('button[type="submit"]');
    submit.disabled = true;
    try {
      await api.upload('/school-content', data);
      modal.close();
      toast('School content published');
      loadSchoolContent();
    } catch (error) {
      submit.disabled = false;
    }
  });
}

const session = startPage('school-content', 'School Content');
if (session) initSchoolContent(session);
