// static/js/library/components/novel-card.js

import { STATUS_STYLE } from './../config.js';
import { getSelectedOverlayMetadata } from './settings.js';
import { CARD_METADATA } from './card-metadata.js';
import { openNovelSync } from './sync.js';
import { escapeHtml } from './../utils.js';
import { deleteNovel } from './../api.js';
import { openNovelEdit } from './edit.js';
import { openNovelReader } from './../views/epub_reader.js';

function renderMeta(icon, value, title = '') {
  if (value === null || value === undefined || value === '' || value === 0 || value === '0' || value === '0/0') return '';

  return `<div class="nt-meta-item" title="${title}"><i class="ti ti-${icon}"></i><span>${value}</span></div>`;
}

function renderTags(tags) {
  if (!tags) return '';

  const values = Array.isArray(tags)
    ? tags
    : String(tags)
        .split(',')
        .map(tag => tag.trim())
        .filter(Boolean);

  if (!values.length) return '';

  return `<div class="nt-card-tags">${values
    .slice(0, 8)
    .map(tag => `<span class="badge bg-white-lt">${tag}</span>`)
    .join('')}</div>`;
}

function renderAction(icon, label, action, extraClass = '', attributes = '') {
  return `
    <button type="button" class="btn btn-sm btn-icon nt-card-action ${extraClass}"data-card-action="${action}"
      title="${label}" aria-label="${label}" ${attributes}>
      <i class="ti ti-${icon}"></i>
    </button>
  `;
}

function showDeleteNovelDialog(novel) {
  const existing = document.getElementById('delete-novel-dialog');

  if (existing) {
    existing.remove();
  }

  const dialog = document.createElement('div');

  dialog.id = 'delete-novel-dialog';
  dialog.className = 'modal modal-blur fade show';
  dialog.style.display = 'block';
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');

  dialog.innerHTML = `
    <div class="modal-dialog modal-sm modal-dialog-centered" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="ti ti-trash me-2"></i>Delete Novel
          </h5>
          <button type="button" class="btn-close" aria-label="Close"></button>
        </div>

        <div class="modal-body">
          <p class="mb-2">Are you sure you want to delete this novel?</p>
          <div class="text-secondary small text-truncate" title="${novel.title}">
            ${novel.title}
          </div>
          <div class="text-danger small mt-2">
            <i class="ti ti-alert-triangle me-1"></i>
            This action cannot be undone.
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-action="cancel">
            Cancel
          </button>
          <button type="button" class="btn btn-danger" data-action="delete">
            <i class="ti ti-trash me-1"></i>Delete
          </button>
        </div>
      </div>
    </div>
  `;

  const close = () => {
    dialog.remove();
  };

  dialog.querySelector('.btn-close').addEventListener('click', close);
  dialog.querySelector('[data-action="cancel"]').addEventListener('click', close);

  dialog.querySelector('[data-action="delete"]').addEventListener('click', async event => {
    const button = event.currentTarget;

    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';

    try {
      const result = await deleteNovel(novel.id);

      close();

      window.showLibraryNotification?.(result.message || 'Novel deleted successfully.', 'success');

      document.dispatchEvent(
        new CustomEvent('library:novel-deleted', {
          detail: { id: novel.id }
        })
      );
    } catch (error) {
      button.disabled = false;
      button.innerHTML = '<i class="ti ti-trash me-1"></i>Delete';

      window.showLibraryNotification?.(error.message || 'Failed to delete the novel.', 'error');
    }
  });

  document.body.appendChild(dialog);
}

// --- Novel links modal -------------------------------------------------

let linksModalEl = null;

function closeNovelLinksDialog() {
  if (!linksModalEl) return;

  linksModalEl.classList.remove('show');
  linksModalEl.style.display = 'none';
  linksModalEl.setAttribute('aria-hidden', 'true');

  document.getElementById('novel-links-backdrop')?.remove();
  document.body.classList.remove('modal-open');
  document.body.style.removeProperty('padding-right');
}

function buildNovelLinksModal() {
  const modal = document.createElement('div');
  modal.id = 'novel-links-dialog';
  modal.className = 'modal modal-blur fade';
  modal.tabIndex = -1;
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  document.body.appendChild(modal);
  return modal;
}

function showNovelLinksDialog(novel) {
  const sourceUrl = novel.source?.url;
  const discordUrl = novel.discord_channel_url;

  if (!sourceUrl && !discordUrl) return;

  if (sourceUrl && !discordUrl) {
    window.open(sourceUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  if (discordUrl && !sourceUrl) {
    window.open(discordUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  if (!linksModalEl) {
    linksModalEl = buildNovelLinksModal();
  }

  const modal = linksModalEl;

  modal.innerHTML = `
    <div class="modal-dialog modal-sm modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="ti ti-link me-2"></i>Novel Links</h5>
          <button type="button" class="btn-close" aria-label="Close" data-novel-links-close></button>
        </div>

        <div class="modal-body">
          <div class="d-grid gap-2">
            ${
              sourceUrl
                ? `
                  <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-outline-primary"><i class="ti ti-world me-2"></i>${novel.source?.name || 'Source'}</a>
                `
                : ''
            }

            ${
              discordUrl
                ? `
                  <a href="${discordUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-outline-primary"><i class="ti ti-brand-discord me-2"></i>Author Discord</a>
                `
                : ''
            }

          </div>
        </div>

      </div>
    </div>
  `;

  // innerHTML was just replaced, so this is always a fresh node —
  // no risk of stacking listeners across calls.
  modal.querySelector('[data-novel-links-close]')?.addEventListener('click', closeNovelLinksDialog);

  modal.addEventListener(
    'click',
    event => {
      if (event.target === modal) closeNovelLinksDialog();
    },
    { once: true }
  );

  if (!document.getElementById('novel-links-backdrop')) {
    const backdrop = document.createElement('div');
    backdrop.id = 'novel-links-backdrop';
    backdrop.className = 'modal-backdrop fade show';
    document.body.appendChild(backdrop);
    backdrop.addEventListener('click', closeNovelLinksDialog, { once: true });
  }

  modal.style.display = 'block';
  modal.classList.add('show');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
}

// --- Card actions (event delegation) ------------------------------------

const CARD_ACTION_HANDLERS = {
  read: novel => openNovelReader(novel.id),
  sync: novel => openNovelSync(novel.id),
  edit: novel => openNovelEdit(novel.id),
  delete: novel => showDeleteNovelDialog(novel),
  links: novel => showNovelLinksDialog(novel)
};

// One listener per container instead of one per button per card — avoids
// the duplicate-binding/duplicate-firing bug that a per-button approach
// gets into if bind*/init* ever run more than once on the same container
// (re-render, pagination, filters, etc.), and scales better with large lists.
function bindContainerDelegation(container, getNovels) {
  if (container.dataset.ntActionsBound === 'true') return;
  container.dataset.ntActionsBound = 'true';

  container.addEventListener('click', event => {
    const button = event.target.closest('.nt-card-action');
    if (!button || !container.contains(button)) return;

    const card = button.closest('.novel-card');
    const action = button.dataset.cardAction;
    const handler = CARD_ACTION_HANDLERS[action];

    if (!card || !handler) return;

    const id = Number(card.dataset.id);
    const novel = getNovels().find(item => item.id === id);
    if (!novel) return;

    event.preventDefault();
    event.stopPropagation();
    handler(novel);
  });
}

// --- Card rendering ----------------------------------

export function renderNovelCard(novel) {
  const unread = novel.reading.unread;

  const status = STATUS_STYLE[novel.status] ?? STATUS_STYLE.Reading;

  const percent = novel.chapters.online > 0 ? Math.round((novel.chapters.local / novel.chapters.online) * 100) : 0;

  const cover = 'cover.webp';

  const selectedOverlayMetadata = new Set(getSelectedOverlayMetadata());

  const optionalMeta = CARD_METADATA.filter(metadata => metadata.overlay && selectedOverlayMetadata.has(metadata.id))
    .map(metadata => {
      const value = metadata.getValue(novel);
      const title = metadata.getTitle ? metadata.getTitle(novel) : metadata.label;

      return renderMeta(metadata.icon, value, title);
    })
    .join('');

  const description = escapeHtml(novel.description || 'No description available.');

  const hasLinks = Boolean(novel.source?.url || novel.discord_channel_url);

  return `
  <div class="col">
    <div class="card novel-card bg-transparent border-0 shadow h-100" data-id="${novel.id}">

      <div class="position-relative novel-cover">

        <img src="static/img/cover/${cover}" class="novel-cover-img card-img-top rounded-1" onerror="this.onerror=null; this.src='static/img/cover/cover.webp';">

        ${unread > 0 ? `<span class="badge bg-red text-white position-absolute top-0 start-0 m-2">+${unread}</span>` : ''}

        <div class="position-absolute top-50 end-0 translate-middle-y me-2 d-flex flex-column align-items-end gap-1">${optionalMeta}</div>

        <div class="position-absolute start-0 ms-2" style="bottom: 20px;">
          <span class="badge ${status.bg} ${status.text} fs-6">${escapeHtml(novel.status)}</span>
        </div>

        <div class="position-absolute bottom-0 start-0 end-0">
          <div class="progress rounded-0 position-relative" style="height: 15px;">
            <div class="progress-bar fw-bold" style="width:${percent}%"></div>
            <span class="position-absolute top-50 start-50 translate-middle fw-bold">
              ${novel.chapters.local}/${novel.chapters.online}
            </span>
          </div>
        </div>


        <div class="novel-card-overlay">
          <div class="novel-card-overlay-content">
            <div class="novel-card-description">${description}</div>
            ${renderTags(novel.tags)}
            <div class="novel-card-actions">
              ${novel.permissions?.can_read ? renderAction('book-2', 'Read', 'read', '', 'data-bs-toggle="modal" data-bs-target="#epub-reader-modal"') : ''}
              ${renderAction('refresh', 'Sync', 'sync', '', 'data-bs-toggle="offcanvas" data-bs-target="#sync-offcanvas"')}
              ${novel.permissions?.can_edit ? renderAction('edit', 'Edit', 'edit') : ''}
              ${novel.permissions?.can_delete ? renderAction('trash', 'Delete', 'delete', 'text-danger') : ''}
              ${hasLinks ? renderAction('link', 'Links', 'links') : ''}
            </div>
          </div>
        </div>
      </div>

      <div class="card-body p-2">

        <div class="nt-title-container" data-bs-toggle="tooltip" data-bs-placement="bottom" title="${escapeHtml(novel.title)}"><div class="nt-title-scroll fw-bold">
            ${escapeHtml(novel.title)}
          </div>
        </div>

        <div class="text-secondary text-truncate text-end small">
          ${escapeHtml(novel.author)}
        </div>

      </div>

    </div>
  </div>
  `;
}

// --- Public binding API (same signatures as before) ---------------------

export function bindNovelCardActions(container, novels) {
  bindContainerDelegation(container, () => novels);
}

export function initNovelCardActions(container) {
  bindContainerDelegation(container, () => window.library?.novels ?? []);
}
