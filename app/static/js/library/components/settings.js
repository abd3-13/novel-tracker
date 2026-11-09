import { escapeHtml } from './../utils.js';
import { saveSetting } from './../api.js';
import { CARD_METADATA } from './card-metadata.js';
import { IMPORT_METADATA, getSelectedImportMetadata, saveSelectedImportMetadata } from './import-metadata.js';

const OVERLAY_STORAGE_KEY = 'library.cardOverlayMetadata';

const OVERLAY_METADATA_IDS = new Set(CARD_METADATA.filter(metadata => metadata.overlay).map(metadata => metadata.id));

const DEFAULT_OVERLAY_METADATA = CARD_METADATA.filter(metadata => metadata.overlay && metadata.overlayDefault).map(metadata => metadata.id);

export function getSelectedOverlayMetadata() {
  const stored = sessionStorage.getItem(OVERLAY_STORAGE_KEY);

  if (!stored) {
    return [...DEFAULT_OVERLAY_METADATA];
  }

  try {
    const parsed = JSON.parse(stored);

    if (!Array.isArray(parsed)) {
      return [...DEFAULT_OVERLAY_METADATA];
    }

    const selected = parsed.filter(id => OVERLAY_METADATA_IDS.has(id));

    return selected.length ? selected : [...DEFAULT_OVERLAY_METADATA];
  } catch {
    return [...DEFAULT_OVERLAY_METADATA];
  }
}

// ---------------------------------------------------------------------------
// Control rendering — dispatch table instead of an if/else ladder.
// Each renderer gets (key, safeValue, metadata) and returns markup.
// ---------------------------------------------------------------------------

function renderReadonlyControl(_key, safeValue) {
  return `
    <div class="input-group">
      <input type="text" class="form-control" value="${escapeHtml(String(safeValue))}" readonly/>
      <span class="input-group-text"><i class="ti ti-lock"></i></span>
    </div>
  `;
}

function renderBooleanControl(key, safeValue) {
  const enabled = ['1', 'true', 'yes', 'on'].includes(String(safeValue).toLowerCase());

  return `
    <label class="form-check form-switch m-0">
      <input class="form-check-input settings-field" type="checkbox" data-setting-key="${key}" ${enabled ? 'checked' : ''}/>
      <span class="form-check-label">${enabled ? 'Enabled' : 'Disabled'}</span>
    </label>
  `;
}

function renderChoiceControl(key, safeValue, metadata) {
  const options = (metadata.options || [])
    .map(
      option =>
        `<option value="${escapeHtml(String(option.value))}" ${String(option.value) === String(safeValue) ? 'selected' : ''}>${escapeHtml(option.label)}</option>`
    )
    .join('');

  return `<select class="form-select settings-field" data-setting-key="${key}">${options}</select>`;
}

function renderNumberControl(key, safeValue, metadata) {
  const min = metadata.min !== undefined ? `min="${metadata.min}"` : '';
  const max = metadata.max !== undefined ? `max="${metadata.max}"` : '';
  const step = metadata.step !== undefined ? `step="${metadata.step}"` : '';

  return `
    <div class="input-group">
      <input type="number" class="form-control settings-field" data-setting-key="${key}" value="${escapeHtml(String(safeValue))}"
        ${min}
        ${max}
        ${step}
      />
      ${metadata.unit ? `<span class="input-group-text">${escapeHtml(metadata.unit)}</span>` : ''}
    </div>
  `;
}

function renderTextControl(key, safeValue, metadata) {
  const type = metadata?.type;
  const inputType = type === 'password' ? 'password' : type === 'url' ? 'url' : 'text';

  return `
    <input type="${inputType}" class="form-control settings-field" data-setting-key="${key}" value="${escapeHtml(String(safeValue))}"
      ${type === 'url' ? 'autocomplete="url"' : ''}
      ${type === 'password' ? 'autocomplete="new-password"' : ''}
      ${metadata.placeholder ? `placeholder="${escapeHtml(metadata.placeholder)}"` : ''}
    />
  `;
}

const CONTROL_RENDERERS = {
  boolean: renderBooleanControl,
  choice: renderChoiceControl,
  number: renderNumberControl
};

function renderSettingControl(key, value, metadata) {
  const safeValue = value ?? '';

  if (metadata?.readonly) {
    return renderReadonlyControl(key, safeValue, metadata);
  }

  const type = metadata?.type || 'string';
  const renderer = CONTROL_RENDERERS[type] || renderTextControl;

  return renderer(key, safeValue, metadata);
}

function renderSettingRow(key, value, metadata) {
  const label = metadata?.label || key;
  const description = metadata?.description || '';
  const icon = metadata?.icon || 'settings';

  return `
    <div class="settings-row py-3">
      <div class="row align-items-center g-3">
        <div class="col">
          <label class="form-label mb-1"><i class="ti ti-${icon} me-1 text-secondary"></i>${escapeHtml(label)}</label>

          ${description ? `<div class="text-secondary small">${escapeHtml(description)}</div>` : ''}
        </div>

        <div class="col-12 col-md-5 col-lg-4">${renderSettingControl(key, value, metadata)}</div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Grouping — computed once per render instead of re-filtering metadata
// for every group (was O(groups * total settings), now O(total settings)).
// ---------------------------------------------------------------------------

function groupSettingKeys(metadata) {
  const groups = new Map();

  for (const [key, definition] of Object.entries(metadata)) {
    const group = definition.group || 'Other';

    if (!groups.has(group)) {
      groups.set(group, []);
    }

    groups.get(group).push(key);
  }

  for (const keys of groups.values()) {
    keys.sort((a, b) => (metadata[a]?.label || a).localeCompare(metadata[b]?.label || b));
  }

  return groups;
}

function renderSettingGroup(group, keys, settings, metadata) {
  if (!keys.length) return '';

  const rows = keys.map(key => renderSettingRow(key, settings[key], metadata[key])).join('');

  return `
    <div class="card mb-3">
      <div class="card-header">
        <div class="d-flex align-items-center gap-2">
          <span class="avatar avatar-sm bg-secondary-lt"><i class="ti ti-settings"></i></span>

          <div>
            <h3 class="card-title mb-0">${escapeHtml(group)}</h3>
            <div class="text-secondary small">Configure ${escapeHtml(group.toLowerCase())} settings.</div>
          </div>
        </div>
      </div>

      <div class="card-body p-0">
        <div class="px-3">${rows}</div>
      </div>
    </div>
  `;
}

function renderOverlaySettings() {
  const selected = new Set(getSelectedOverlayMetadata());
  const overlayOptions = CARD_METADATA.filter(metadata => metadata.overlay);

  return `
    <div class="card mb-3">
      <div class="card-header">
        <div class="d-flex align-items-center gap-3">
          <span class="avatar avatar-sm bg-primary-lt"><i class="ti ti-layout-grid"></i></span>

          <div>
            <h3 class="card-title mb-0">Card overlay metadata</h3>
            <div class="text-secondary small">Choose which metadata appears on novel cards.</div>
          </div>
        </div>
      </div>

      <div class="card-body">
        <div class="form-selectgroup form-selectgroup-boxes d-flex flex-wrap gap-1">
          ${overlayOptions
            .map(
              option => `
                <label class="form-selectgroup-item flex-fill">
                  <input type="checkbox" class="form-selectgroup-input settings-overlay-toggle" data-setting-value="${option.id}" ${selected.has(option.id) ? 'checked' : ''}/>

                  <span class="form-selectgroup-label d-flex align-items-center justify-content-center gap-1 p-2"><i class="ti ti-${option.icon}"></i>${escapeHtml(option.label)}</span>
                </label>
              `
            )
            .join('')}
        </div>

        <div class="alert alert-info-lt mt-3 mb-0" role="alert">
          <div class="d-flex gap-2">
            <i class="ti ti-info-circle"></i>
            <div>
              <div class="fw-semibold">Session setting</div>
              <div class="small">These options apply only to this browser session and are not saved to the database.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderImportRowSettings() {
  const selected = new Set(getSelectedImportMetadata());

  return `
    <div class="card mb-3">
      <div class="card-header">
        <div class="d-flex align-items-center gap-3">
          <span class="avatar avatar-sm bg-primary-lt"><i class="ti ti-list-details"></i></span>

          <div>
            <h3 class="card-title mb-0">Import row details</h3>
            <div class="text-secondary small">Choose which metadata appears in the import result list.</div>
          </div>
        </div>
      </div>

      <div class="card-body">
        <div class="form-selectgroup form-selectgroup-boxes d-flex flex-wrap gap-1">
          ${IMPORT_METADATA.map(
            option => `
              <label class="form-selectgroup-item flex-fill">
                <input type="checkbox" class="form-selectgroup-input settings-import-toggle" data-setting-value="${option.id}" ${selected.has(option.id) ? 'checked' : ''}/>

                <span class="form-selectgroup-label d-flex align-items-center justify-content-center gap-1 p-2"><i class="ti ti-${option.icon}"></i>${escapeHtml(option.label)}</span>
              </label>
            `
          ).join('')}
        </div>

        <div class="alert alert-info-lt mt-3 mb-0" role="alert">
          <div class="d-flex gap-2">
            <i class="ti ti-info-circle"></i>
            <div>
              <div class="fw-semibold">Saved in this browser</div>
              <div class="small">These options persist across sessions. The filename is always shown.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function renderSettingsPanel() {
  const container = document.getElementById('library-settings-content');

  if (!container) return;

  const settings = window.librarySettings || {};
  const metadata = window.librarySettingsMetadata || {};

  const grouped = groupSettingKeys(metadata);
  const sortedGroupNames = [...grouped.keys()].sort((a, b) => a.localeCompare(b));

  const settingsContent = sortedGroupNames.map(group => renderSettingGroup(group, grouped.get(group), settings, metadata)).join('');

  container.innerHTML = `
    ${renderOverlaySettings()}
    ${renderImportRowSettings()}
    ${settingsContent}

    <div class="settings-save-bar">
      <div class="d-flex align-items-center justify-content-between gap-3">
        <div class="text-secondary small"><i class="ti ti-database me-1"></i>Database settings are saved explicitly.</div>

        <button type="button" class="btn btn-primary" id="save-settings"><i class="ti ti-device-floppy me-1"></i>Save settings</button>
      </div>
    </div>
  `;

  bindSettingsEvents();
}

function bindSettingsEvents() {
  const saveButton = document.getElementById('save-settings');

  if (saveButton) {
    saveButton.addEventListener('click', saveSettings);
  }

  document.querySelectorAll('.settings-overlay-toggle').forEach(input => {
    input.addEventListener('change', saveOverlaySettings);
  });

  document.querySelectorAll('.settings-import-toggle').forEach(input => {
    input.addEventListener('change', saveImportRowSettings);
  });
}

async function saveSettings() {
  const fields = document.querySelectorAll('.settings-field');
  const updates = [];

  fields.forEach(field => {
    const key = field.dataset.settingKey;

    if (!key) return;

    const value = field.type === 'checkbox' ? (field.checked ? '1' : '0') : field.value;
    const original = window.librarySettings?.[key];

    if (String(original ?? '') !== String(value)) {
      updates.push({ key, value });
    }
  });

  if (!updates.length) {
    window.showLibraryNotification?.('No setting changes to save.', 'info');
    return;
  }

  saveButtonState(true);

  try {
    for (const update of updates) {
      const result = await saveSetting(update.key, update.value);

      if (window.librarySettings) {
        window.librarySettings[update.key] = result.data?.[update.key] ?? update.value;
      }
    }

    window.showLibraryNotification?.(`${updates.length} setting${updates.length === 1 ? '' : 's'} saved successfully.`, 'success');
  } catch (error) {
    window.showLibraryNotification?.(error.message || 'Failed to save settings.', 'error');
  } finally {
    saveButtonState(false);
  }
}

function saveButtonState(saving) {
  const button = document.getElementById('save-settings');

  if (!button) return;

  button.disabled = saving;
  button.innerHTML = saving ? `<span class="spinner-border spinner-border-sm me-1"></span>Saving...` : `<i class="ti ti-device-floppy me-1"></i>Save settings`;
}

function saveOverlaySettings() {
  const selected = Array.from(document.querySelectorAll('.settings-overlay-toggle:checked')).map(input => input.dataset.settingValue);

  if (!selected.length) {
    window.showLibraryNotification?.('Select at least one overlay item.', 'warning');
    renderSettingsPanel();
    return;
  }

  sessionStorage.setItem(OVERLAY_STORAGE_KEY, JSON.stringify(selected));

  document.dispatchEvent(new CustomEvent('library:overlay-settings-changed', { detail: { selected } }));

  window.showLibraryNotification?.('Card overlay settings updated.', 'success');
}

function saveImportRowSettings() {
  const selected = Array.from(document.querySelectorAll('.settings-import-toggle:checked')).map(input => input.dataset.settingValue);

  if (!selected.length) {
    window.showLibraryNotification?.('Select at least one import detail.', 'warning');
    renderSettingsPanel();
    return;
  }

  saveSelectedImportMetadata(selected);

  document.dispatchEvent(new CustomEvent('library:import-row-settings-changed', { detail: { selected } }));

  window.showLibraryNotification?.('Import row details updated.', 'success');
}

export function initSettingsPanel() {
  const panel = document.getElementById('library-settings-panel');

  if (!panel) return;

  renderSettingsPanel();
}
