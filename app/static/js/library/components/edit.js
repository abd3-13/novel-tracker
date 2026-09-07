import { fetchNovel, updateNovel } from './../api.js';
import { escapeHtml } from './../utils.js';

const STATUS_OPTIONS = ['Reading', 'Completed', 'Hiatus', 'Dropped', 'Planned'];

function fieldInput(key, label, value, options = {}) {
  const { type = 'text', icon = 'edit', placeholder = '', readonly = false, min = '', step = '' } = options;

  return `
    <div class="mb-3">
      <label class="form-label">
        <i class="ti ti-${icon} me-1 text-secondary"></i>${label}
      </label>

      <input
        type="${type}"
        class="form-control novel-edit-field"
        data-field="${key}"
        value="${escapeHtml(value ?? '')}"
        ${placeholder ? `placeholder="${escapeHtml(placeholder)}"` : ''}
        ${min !== '' ? `min="${min}"` : ''}
        ${step !== '' ? `step="${step}"` : ''}
        ${readonly ? 'readonly' : ''}
      />
    </div>
  `;
}

function textareaField(key, label, value, options = {}) {
  const { icon = 'align-left', rows = 4, placeholder = '' } = options;

  return `
    <div class="mb-3">
      <label class="form-label">
        <i class="ti ti-${icon} me-1 text-secondary"></i>${label}
      </label>

      <textarea
        class="form-control novel-edit-field"
        data-field="${key}"
        rows="${rows}"
        ${placeholder ? `placeholder="${escapeHtml(placeholder)}"` : ''}
      >${escapeHtml(value ?? '')}</textarea>
    </div>
  `;
}

function selectField(key, label, value, options = {}) {
  const { icon = 'circle-check', choices = [] } = options;

  return `
    <div class="mb-3">
      <label class="form-label">
        <i class="ti ti-${icon} me-1 text-secondary"></i>${label}
      </label>

      <select class="form-select novel-edit-field" data-field="${key}">
        ${choices
          .map(
            choice => `
            <option value="${escapeHtml(choice)}" ${String(choice) === String(value ?? '') ? 'selected' : ''}>
              ${escapeHtml(choice)}
            </option>
          `
          )
          .join('')}
      </select>
    </div>
  `;
}

function renderEditModal(novel) {
  const existing = document.getElementById('novel-edit-modal');

  if (existing) {
    existing.remove();
  }

  const modal = document.createElement('div');

  modal.id = 'novel-edit-modal';
  modal.className = 'modal modal-blur fade';
  modal.tabIndex = -1;
  modal.setAttribute('role', 'dialog');

  modal.innerHTML = `
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable" role="document">
      <div class="modal-content">

        <div class="modal-header">
          <div>
            <h5 class="modal-title"><i class="ti ti-edit me-2"></i>Edit Novel</h5>
            <div class="text-secondary small mt-1">Novel #${escapeHtml(novel.id)} · ${escapeHtml(novel.name || novel.title || '')}</div>
          </div>

          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>

        <div class="modal-body">

          <div class="alert alert-info-lt mb-4">
            <div class="d-flex gap-2">
              <i class="ti ti-info-circle"></i>
              <div>
                <div class="fw-semibold">Edit library record</div>
                <div class="small">
                  Changes are saved directly to this novel's database record.
                  Fields managed automatically by synchronization may be overwritten during the next sync.
                </div>
              </div>
            </div>
          </div>

          <!-- Identity -->
          <div class="card mb-3">
            <div class="card-header">
              <div class="d-flex align-items-center gap-2">
                <span class="avatar avatar-sm bg-primary-lt"><i class="ti ti-book"></i></span>

                <div>
                  <h3 class="card-title mb-0">Novel information</h3>
                  <div class="text-secondary small">Title, author, status and source.</div>
                </div>
              </div>
            </div>

            <div class="card-body">
              <div class="row">

                <div class="col-md-6">
                  ${fieldInput('name', 'Novel title', novel.name, { icon: 'book', placeholder: 'Novel title' })}

                  ${fieldInput('author', 'Author', novel.author, { icon: 'user', placeholder: 'Author name' })}

                  ${selectField('status', 'Status', novel.status, { icon: 'circle-check', choices: STATUS_OPTIONS })}

                  ${fieldInput('tags', 'Tags', novel.tags, { icon: 'tags', placeholder: 'tag1, tag2, tag3' })}
                </div>

                <div class="col-md-6">
                  ${fieldInput('source', 'Source', novel.source, { icon: 'world', placeholder: 'WebNovel' })}

                  ${fieldInput('url', 'Source URL', novel.url, { type: 'url', icon: 'link', placeholder: 'https://...' })}

                  ${fieldInput('cover_path', 'Cover file', novel.cover_path, { icon: 'photo', placeholder: 'Cover filename' })}

                  ${fieldInput('discord_channel_url', 'Discord URL', novel.discord_channel_url, { type: 'url', icon: 'brand-discord', placeholder: 'https://...' })}
                </div>

              </div>

              ${textareaField('description', 'Description', novel.description, { icon: 'align-left', rows: 5, placeholder: 'Novel description...' })}


              ${textareaField('notes', 'Notes', novel.notes, { icon: 'notes', rows: 4, placeholder: 'Personal notes about this novel...' })}
            </div>
          </div>

          <!-- Chapters -->
          <div class="card mb-3">
            <div class="card-header">
              <div class="d-flex align-items-center gap-2">
                <span class="avatar avatar-sm bg-green-lt"><i class="ti ti-books"></i></span>

                <div>
                  <h3 class="card-title mb-0">Chapter tracking</h3>
                  <div class="text-secondary small">Local, online and reading progress.</div>
                </div>
              </div>
            </div>

            <div class="card-body">
              <div class="row">

                <div class="col-md-4">${fieldInput('localchap', 'Local chapters', novel.localchap, { type: 'number', icon: 'book-2', min: '0' })}</div>

                <div class="col-md-4">${fieldInput('onlinechap', 'Online chapters', novel.onlinechap, { type: 'number', icon: 'cloud', min: '0' })}</div>

                <div class="col-md-4">${fieldInput('progress', 'Current chapter', novel.progress, { type: 'number', icon: 'bookmark', min: '0' })}</div>

              </div>

              <div class="row">
                <div class="col-md-6">${fieldInput('latestchaptime', 'Latest online chapter time', novel.latestchaptime, { icon: 'clock', placeholder: 'YYYY-MM-DD HH:MM:SS' })}</div>

                <div class="col-md-6">${fieldInput('progress_updated', 'Progress updated', novel.progress_updated, { icon: 'clock-edit', placeholder: 'YYYY-MM-DD HH:MM:SS' })}</div>
              </div>
            </div>
          </div>

          <!-- EPUB -->
          <div class="card mb-3">
            <div class="card-header">
              <div class="d-flex align-items-center gap-2">
                <span class="avatar avatar-sm bg-purple-lt"><i class="ti ti-file-text"></i></span>

                <div>
                  <h3 class="card-title mb-0">EPUB & local files</h3>
                  <div class="text-secondary small">Local EPUB and extracted chapter information.</div>
                </div>
              </div>
            </div>

            <div class="card-body">
              ${fieldInput('filepath', 'EPUB file path', novel.filepath, { icon: 'file', placeholder: 'filename.epub' })}

              <div class="row">
                <div class="col-md-6">${fieldInput('local_lastchaptitle', 'Last local chapter title', novel.local_lastchaptitle, { icon: 'bookmark', placeholder: 'Last chapter title' })}</div>

                <div class="col-md-6">${fieldInput('local_lastchapfile', 'Last local chapter file', novel.local_lastchapfile, { icon: 'file-text', placeholder: 'chapter.xhtml' })}</div>
              </div>

              <div class="form-check form-switch">
                <input class="form-check-input novel-edit-field" type="checkbox" data-field="epub_exists" ${Number(novel.epub_exists) ? 'checked' : ''}/>
                <label class="form-check-label">EPUB exists</label>
              </div>
            </div>
          </div>

          <!-- Characters -->
          <div class="card mb-3">
            <div class="card-header">
              <div class="d-flex align-items-center gap-2">
                <span class="avatar avatar-sm bg-orange-lt"><i class="ti ti-users"></i></span>

                <div>
                  <h3 class="card-title mb-0">Characters</h3>
                  <div class="text-secondary small">Character counts stored for this novel.</div>
                </div>
              </div>
            </div>

            <div class="card-body">
              <div class="row">
                <div class="col-md-6">${fieldInput('characters', 'Local characters', novel.characters, { type: 'number', icon: 'users', min: '0' })}</div>

                <div class="col-md-6">${fieldInput('online_characters', 'Online characters', novel.online_characters, { type: 'number', icon: 'cloud', min: '0' })}</div>
              </div>
            </div>
          </div>

          <!-- System -->
          <div class="card">
            <div class="card-header">
              <div class="d-flex align-items-center gap-2">
                <span class="avatar avatar-sm bg-secondary-lt">
                  <i class="ti ti-database"></i>
                </span>

                <div>
                  <h3 class="card-title mb-0">Database information</h3>
                  <div class="text-secondary small">Advanced fields from the database record.</div>
                </div>
              </div>
            </div>

            <div class="card-body">
              <div class="row">

                <div class="col-md-6">
                  ${fieldInput('id', 'Novel ID', novel.id, { type: 'number', icon: 'id', readonly: true })}

                  ${fieldInput('created_time', 'Created', novel.created_time, { icon: 'calendar-plus', readonly: true })}
                </div>

                <div class="col-md-6">
                  ${fieldInput('last_updated', 'Last updated', novel.last_updated, { icon: 'clock', readonly: true })}

                  ${fieldInput('updated_count', 'Update count', novel.updated_count, { type: 'number', icon: 'history', readonly: true })}
                </div>

              </div>
            </div>
          </div>

        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>

          <button type="button" class="btn btn-primary" data-action="save"><i class="ti ti-device-floppy me-1"></i>Save changes</button>
        </div>

      </div>
    </div>
  `;

  document.body.appendChild(modal);

  return modal;
}

function collectChanges(modal, novel) {
  const updates = {};

  modal.querySelectorAll('.novel-edit-field').forEach(field => {
    const key = field.dataset.field;

    if (!key || key === 'id' || field.readOnly) return;

    const value = field.type === 'checkbox' ? (field.checked ? 1 : 0) : field.value;

    if (String(value ?? '') !== String(novel[key] ?? '')) {
      updates[key] = value;
    }
  });

  return updates;
}

async function saveNovel(modal, novel) {
  const saveButton = modal.querySelector('[data-action="save"]');
  const updates = collectChanges(modal, novel);

  if (!Object.keys(updates).length) {
    window.showLibraryNotification?.('No changes to save.', 'info');
    return;
  }

  saveButton.disabled = true;
  saveButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

  try {
    const result = await updateNovel(novel.id, updates);

    window.showLibraryNotification?.(result.message || 'Novel updated successfully.', 'success');

    modal.querySelector('[data-bs-dismiss="modal"]')?.click();

    document.dispatchEvent(
      new CustomEvent('library:novel-updated', {
        detail: {
          id: novel.id,
          data: result.data
        }
      })
    );
  } catch (error) {
    saveButton.disabled = false;
    saveButton.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Save changes';

    window.showLibraryNotification?.(error.message || 'Failed to update novel.', 'error');
  }
}

export async function openNovelEdit(novelId) {
  try {
    const novel = await fetchNovel(novelId);
    const modal = renderEditModal(novel);

    modal.querySelector('[data-action="save"]').addEventListener('click', () => {
      saveNovel(modal, novel);
    });

    const trigger = document.createElement('button');

    trigger.type = 'button';
    trigger.className = 'd-none';
    trigger.setAttribute('data-bs-toggle', 'modal');
    trigger.setAttribute('data-bs-target', '#novel-edit-modal');

    document.body.appendChild(trigger);
    trigger.click();
    trigger.remove();

    modal.addEventListener(
      'hidden.bs.modal',
      () => {
        modal.remove();
      },
      { once: true }
    );
  } catch (error) {
    window.showLibraryNotification?.(error.message || 'Failed to load novel.', 'error');
  }
}
