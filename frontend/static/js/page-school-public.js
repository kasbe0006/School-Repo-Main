const mount = document.getElementById('public-content');

function escapePublic(value) {
  const node = document.createElement('span');
  node.textContent = value ?? '';
  return node.innerHTML;
}

function publicCard(item) {
  const media = item.image_url
    ? `<img src="${escapePublic(item.image_url)}" alt="" class="w-full h-48 object-cover rounded-lg mb-4">`
    : item.video_url
      ? `<video src="${escapePublic(item.video_url)}" controls class="w-full h-48 object-cover rounded-lg mb-4"></video>`
      : '';
  const date = item.event_date
    ? `<p class="text-xs text-muted mt-3">${escapePublic(item.event_date)}${item.event_end_date ? ` – ${escapePublic(item.event_end_date)}` : ''}${item.location ? ` · ${escapePublic(item.location)}` : ''}</p>`
    : '';
  const details = [
    item.documents_required ? `<p><strong>Documents needed:</strong> ${escapePublic(item.documents_required)}</p>` : '',
    item.scholarship_info ? `<p><strong>Scholarships:</strong> ${escapePublic(item.scholarship_info)}</p>` : '',
  ].join('');
  return `<article class="bg-white rounded-xl border border-line shadow-sm p-5">${media}
    <p class="text-xs font-semibold uppercase tracking-wide text-primary-600">${escapePublic(item.kind)}</p>
    <h2 class="text-lg font-semibold text-ink mt-1">${escapePublic(item.title)}</h2>
    <p class="text-sm text-slate-600 whitespace-pre-line mt-3">${escapePublic(item.description)}</p>
    ${date}${details ? `<div class="text-xs text-slate-600 space-y-1 mt-3">${details}</div>` : ''}
  </article>`;
}

async function loadPublicContent() {
  try {
    const [configResponse, contentResponse] = await Promise.all([
      fetch('/api/config'),
      fetch('/api/school-content/public?limit=100&sort=created_at&order=desc'),
    ]);
    if (!configResponse.ok || !contentResponse.ok) throw new Error('Unable to load school information');
    const config = await configResponse.json();
    const content = await contentResponse.json();
    document.title = config.school_short_name;
    document.querySelectorAll('[data-school-name]').forEach((el) => { el.textContent = config.school_name; });
    document.querySelectorAll('[data-school-tagline]').forEach((el) => { el.textContent = config.school_tagline; });
    document.querySelectorAll('[data-school-logo]').forEach((el) => {
      if (config.logo_url) {
        el.src = config.logo_url;
        el.classList.remove('hidden');
      }
    });
    mount.innerHTML = content.items.length
      ? content.items.map(publicCard).join('')
      : '<div class="md:col-span-2 bg-white rounded-xl border border-line p-10 text-center text-muted">School information will be published here soon.</div>';
  } catch (error) {
    mount.innerHTML = `<div class="md:col-span-2 bg-white rounded-xl border border-red-200 p-10 text-center text-danger">${escapePublic(error.message)}</div>`;
  }
}

loadPublicContent();
