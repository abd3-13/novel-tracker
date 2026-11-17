// components/header.js
import { deleteMissingEpubs } from './../api.js';
import { escapeHtml } from './../utils.js';
import { IS_ADMIN } from './../permissions.js';

function showMissingEpubDialog(missingNovels) {
  const count = missingNovels.length;

  if (count <= 0) {
    window.showLibraryNotification?.('There are no missing EPUB records to clean up.', 'info');
    return;
  }

  document.getElementById('missing-epub-dialog')?.remove();
  document.getElementById('missing-epub-backdrop')?.remove();
  document.body.classList.remove('modal-open');

  const novelRows = missingNovels
    .map(novel => {
      const title = escapeHtml(novel.title || 'Untitled');
      const path = novel.epub?.path ? escapeHtml(novel.epub.path) : '';

      return `
        <div class="list-group-item px-0 py-2">
          <div class="text-truncate" title="${title}">${title}</div>
          ${path ? `<div class="text-secondary small text-truncate" title="${path}">${path}</div>` : ''}
        </div>
      `;
    })
    .join('');

  const dialog = document.createElement('div');
  const backdrop = document.createElement('div');

  dialog.id = 'missing-epub-dialog';
  dialog.className = 'modal modal-blur fade show';
  dialog.style.display = 'block';
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');

  backdrop.id = 'missing-epub-backdrop';
  backdrop.className = 'modal-backdrop fade show';

  dialog.innerHTML = `
    <div class="modal-dialog modal-dialog-centered" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="ti ti-file-alert me-2"></i>Clean up missing EPUBs
          </h5>
          <button type="button" class="btn-close" aria-label="Close"></button>
        </div>

        <div class="modal-body">
          <p class="mb-1">
            ${count} novel${count === 1 ? ' has' : 's have'} a missing EPUB file.
          </p>
          <div class="text-secondary small">
            ${count === 1 ? 'It' : 'They'} will be flagged as deleted and hidden from the library.
            The database ${count === 1 ? 'record stays' : 'records stay'} intact.
          </div>

          <div class="list-group list-group-flush missing-epub-list mt-3">
            ${novelRows}
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-action="cancel">
            Cancel
          </button>
          <button type="button" class="btn btn-danger" data-action="cleanup">
            <i class="ti ti-trash me-1"></i>Flag ${count} record${count === 1 ? '' : 's'}
          </button>
        </div>
      </div>
    </div>
  `;

  const close = () => {
    dialog.remove();
    backdrop.remove();
    document.body.classList.remove('modal-open');
    document.removeEventListener('keydown', onKeydown);
  };

  function onKeydown(event) {
    if (event.key === 'Escape') {
      close();
    }
  }

  dialog.querySelector('.btn-close').addEventListener('click', close);
  dialog.querySelector('[data-action="cancel"]').addEventListener('click', close);
  backdrop.addEventListener('click', close);

  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      close();
    }
  });

  document.addEventListener('keydown', onKeydown);

  dialog.querySelector('[data-action="cleanup"]').addEventListener('click', async event => {
    const button = event.currentTarget;

    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cleaning up...';

    try {
      const result = await deleteMissingEpubs();

      close();

      window.showLibraryNotification?.(result.message || 'Missing EPUB records cleaned up.', 'success');

      document.dispatchEvent(
        new CustomEvent('library:novel-deleted', {
          detail: { cleanup: true, count: result.data?.deleted ?? 0 }
        })
      );
    } catch (error) {
      button.disabled = false;
      button.innerHTML = `<i class="ti ti-trash me-1"></i>Flag ${count} record${count === 1 ? '' : 's'}`;

      window.showLibraryNotification?.(error.message || 'Failed to clean up missing EPUB records.', 'error');
    }
  });

  document.body.classList.add('modal-open');
  document.body.appendChild(backdrop);
  document.body.appendChild(dialog);
}

export function renderHeader(library) {
  const missingNovels = library.novels.filter(novel => !novel.epub?.exists);
  const missingEpub = missingNovels.length;

  const user = window.libraryUser || {};
  const userName = user.username || 'Account';
  const userRole = user.role ? `${user.role.charAt(0).toUpperCase()}${user.role.slice(1)}` : '';

  document.getElementById('library-header').innerHTML = `
      <div class="row align-items-center">
        <div class="col">
          <h2 class="page-title mb-1">Library<div id="tile_server_stat"><span class="status status-red"><span class="status-dot status-dot-animated"></span> Server</span></div></h2>
          <div class="text-secondary"><span>${library.stats.total} Novels</span><span class="mx-2">•</span><span>${library.stats.filter} Filtered</span><span class="mx-2">•</span><span>${library.stats.updates} Updates</span>${missingEpub > 0 && IS_ADMIN ? `<span class="mx-2">•</span><button type="button" id="library-missing-epub" class="library-missing-epub" title="Clean up records whose EPUB file is missing"><i class="ti ti-file-alert me-1"></i>${missingEpub} Missing EPUB</button>` : ''}</div>
        </div>
        <div class="col-auto">
          <div class="d-flex align-items-center gap-2">
            <button class="btn btn-icon btn-ghost-secondary fs-1" title="Settings" data-bs-toggle="offcanvas" data-bs-target="#library-settings-panel"><i class="ti ti-settings"></i></button>
            <div class="dropdown">
              <a href="#" class="fs-1 d-flex align-items-center text-reset text-decoration-none m-0 border-0" data-bs-toggle="dropdown"><i class="avatar avatar-lg ti ti-user"></i></a>
              <div class="dropdown-menu dropdown-menu-end">
                <div class="dropdown-header">${escapeHtml(userName)}${userRole ? `<div class="text-secondary small">${escapeHtml(userRole)}</div>` : ''}</div>
                <a class="dropdown-item" href="#">Profile</a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item text-danger" href="/logout">Logout</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

  document
    .getElementById('library-missing-epub')
    ?.addEventListener('click', () => showMissingEpubDialog(missingNovels));
}
