const CONTENT_KINDS = [
  { value: 'notice', label: 'Notice' },
  { value: 'activity', label: 'Activity / Event' },
  { value: 'gallery', label: 'Photo / Video' },
  { value: 'admission', label: 'Admission information' },
];

function initSchoolContent({ content, user }) {
  content.innerHTML = pageHeader(
    'School Content',
    'Publish notices, activities, event details, gallery media, admission requirements and scholarship information.',
    user.role === 'admin'
      ? `<button type="button" id="new-content" class="${btnClass('primary')}">${icon('plus', 16)} Add content</button>`
      : '',
  ) + `<div id="content-list">${card(skeletonCards(3))}</div>`;
  loadSchoolContent();
  document.getElementById('new-content')?.addEventListener('click', openContentForm);
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
    refreshIcons();
  } catch (error) {
    showError(mount, error, loadSchoolContent);
  }
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
      ${getUser()?.role === 'admin' ? `<button type="button" data-delete-content="${item.id}" class="${btnClass('danger', 'sm')}">${icon('trash-2', 14)}</button>` : ''}
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
