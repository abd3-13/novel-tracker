import { FILTER_MAP } from './config.js';

export function timeAgo(dateString) {
  if (!dateString || dateString === '0') return '';

  const now = new Date();
  const date = new Date(dateString);

  let diff = Math.floor((now - date) / 1000);

  const units = [
    { label: 'y', secs: 31536000 },
    { label: 'mo', secs: 2592000 },
    { label: 'w', secs: 604800 },
    { label: 'd', secs: 86400 },
    { label: 'h', secs: 3600 },
    { label: 'm', secs: 60 },
    { label: 's', secs: 1 }
  ];

  for (const unit of units) {
    const value = Math.floor(diff / unit.secs);
    if (value >= 1) return `${value}${unit.label}`;
  }

  return 'now';
}

export function applySearch(library) {
  const search = library.search.trim().toLowerCase();

  if (!search) return;

  library.visible = library.visible.filter(novel => {
    return [novel.title, novel.author, novel.description, novel.tags, novel.notes].some(value =>
      String(value || '')
        .toLowerCase()
        .includes(search)
    );
  });
}

export function getValue(novel, field) {
  const definition = FILTER_MAP.get(field);
  return definition ? definition.getter(novel) : '';
}

let filterId = 0;

export function nextFilterId() {
  return ++filterId;
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Only http(s) URLs may reach an href or window.open(). Novel metadata comes
// from external files, so a "javascript:" URL must never become a link.
export function safeUrl(value, fallback = '#') {
  if (!value) return fallback;

  try {
    const url = new URL(String(value), window.location.origin);

    return ['http:', 'https:'].includes(url.protocol) ? url.href : fallback;
  } catch {
    return fallback;
  }
}
