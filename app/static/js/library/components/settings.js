import { escapeHtml } from './../utils.js';

const OVERLAY_METADATA_OPTIONS = [
  { id: 'characters', label: 'Characters', icon: 'users' },
  { id: 'progress', label: 'Read progress', icon: 'percentage' },
  { id: 'chapter', label: 'Current chapter', icon: 'bookmark' },
  { id: 'updates', label: 'New chapters', icon: 'bookmarks' },
  { id: 'time', label: 'Last update', icon: 'clock' }
];

const OVERLAY_STORAGE_KEY = 'library.cardOverlayMetadata';

const DEFAULT_OVERLAY_METADATA = ['characters', 'progress', 'chapter', 'updates', 'time'];

function parseOverlayMetadata(rawValue) {
  if (!rawValue) return DEFAULT_OVERLAY_METADATA;

  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) && parsed.length ? parsed : DEFAULT_OVERLAY_METADATA;
  } catch {
    return DEFAULT_OVERLAY_METADATA;
  }
}

export function getSelectedOverlayMetadata() {
  const stored = sessionStorage.getItem(OVERLAY_STORAGE_KEY);

  if (stored) {
    return parseOverlayMetadata(stored);
  }

  return [...DEFAULT_OVERLAY_METADATA];
}

function renderSettingControl(key, value, metadata) {
  console.count('renderSettingControl');
  const type = metadata?.type || 'string';
  const safeValue = value ?? '';

  if (metadata?.readonly) {
    return `
      <input
        type="text"
        class="form-control"
        value="${escapeHtml(String(safeValue))}"
        readonly
      />
    `;
  }

  if (type === 'boolean') {
    const enabled = ['1', 'true', 'yes', 'on'].includes(String(safeValue).toLowerCase());

    return `
      <label class="form-check form-switch mb-0">
        <input
          class="form-check-input settings-field"
          type="checkbox"
          data-setting-key="${key}"
          ${enabled ? 'checked' : ''}
        />
        <span class="form-check-label">
          ${enabled ? 'Enabled' : 'Disabled'}
        </span>
      </label>
    `;
  }

  if (type === 'choice') {
    const options = (metadata.options || [])
      .map(
        option => `
        <option
          value="${escapeHtml(String(option.value))}"
          ${String(option.value) === String(safeValue) ? 'selected' : ''}
        >
          ${escapeHtml(option.label)}
        </option>
      `
      )
      .join('');

    return `
      <select
        class="form-select settings-field"
        data-setting-key="${key}"
      >
        ${options}
      </select>
    `;
  }

  if (type === 'number') {
    const min = metadata.min !== undefined ? `min="${metadata.min}"` : '';
    const max = metadata.max !== undefined ? `max="${metadata.max}"` : '';
    const step = metadata.step !== undefined ? `step="${metadata.step}"` : '';

    return `
      <input
        type="number"
        class="form-control settings-field"
        data-setting-key="${key}"
        value="${escapeHtml(String(safeValue))}"
        ${min}
        ${max}
        ${step}
      />
    `;
  }

  const inputType = type === 'password' ? 'password' : type === 'url' ? 'url' : 'text';

  return `
    <input
      type="${inputType}"
      class="form-control settings-field"
      data-setting-key="${key}"
      value="${escapeHtml(String(safeValue))}"
      ${type === 'url' ? 'autocomplete="url"' : ''}
    />
  `;
}

function renderSettingRow(key, value, metadata) {
  console.count('renderSettingGroup');
  const label = metadata?.label || key;
  const description = metadata?.description || '';
  const icon = metadata?.icon || 'settings';

  return `
    <div class="mb-4">
      <div class="row align-items-center">
        <div class="col">
          <label class="form-label mb-1">
            <i class="ti ti-${icon} me-1 text-secondary"></i>
            ${escapeHtml(label)}
          </label>

          ${description ? `<div class="text-secondary small">${escapeHtml(description)}</div>` : ''}
        </div>

        <div class="col-auto" style="min-width: 220px">
          ${renderSettingControl(key, value, metadata)}
        </div>
      </div>
    </div>
  `;
}

function renderSettingGroup(group, settings, metadata) {
  console.count('renderSettingGroup');
  const entries = Object.entries(metadata)
    .filter(([, definition]) => (definition.group || 'Other') === group)
    .sort(([a], [b]) => {
      const labelA = metadata[a]?.label || a;
      const labelB = metadata[b]?.label || b;
      return labelA.localeCompare(labelB);
    });

  if (!entries.length) return '';

  const rows = entries.map(([key]) => renderSettingRow(key, settings[key], metadata[key])).join('');

  return `
    <div class="card mb-3">
      <div class="card-header">
        <div class="d-flex align-items-center gap-2">
          <i class="ti ti-settings text-secondary"></i>
          <h3 class="card-title">${escapeHtml(group)}</h3>
        </div>
      </div>

      <div class="card-body">
        ${rows}
      </div>
    </div>
  `;
}

function renderOverlaySettings() {
  const selected = new Set(getSelectedOverlayMetadata());

  return `
    <div class="card mb-3">
      <div class="card-header">
        <div>
          <h3 class="card-title">Card overlay metadata</h3>
          <div class="text-secondary small">
            Choose which metadata appears on novel cards.
          </div>
        </div>
      </div>

      <div class="card-body">
        <div class="form-selectgroup form-selectgroup-boxes d-flex flex-wrap gap-2">
          ${OVERLAY_METADATA_OPTIONS.map(
            option => `
            <label class="form-selectgroup-item flex-fill">
              <input
                type="checkbox"
                class="form-selectgroup-input settings-overlay-toggle"
                data-setting-value="${option.id}"
                ${selected.has(option.id) ? 'checked' : ''}
              />

              <span class="form-selectgroup-label d-flex align-items-center justify-content-center gap-2 py-3">
                <i class="ti ti-${option.icon}"></i>
                ${option.label}
              </span>
            </label>
          `
          ).join('')}
        </div>

        <div class="text-secondary small mt-3">
          These settings apply only to this browser session.
        </div>
      </div>
    </div>
  `;
}

export function renderSettingsPanel() {
  const settings = window.librarySettings || {};
  const metadata = window.librarySettingsMetadata || {};

  const groups = [...new Set(Object.values(metadata).map(definition => definition.group || 'Other'))];

  const settingsContent = groups
    .sort((a, b) => a.localeCompare(b))
    .map(group => renderSettingGroup(group, settings, metadata))
    .join('');

  document.getElementById('library-settings-content').innerHTML = `
    ${renderOverlaySettings()}
    ${settingsContent}

    <div class="settings-save-bar">
      <div class="d-flex justify-content-end">
        <button type="button" class="btn btn-primary" id="save-settings">
          <i class="ti ti-device-floppy me-1"></i>
          Save settings
        </button>
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
}

export async function saveSettings(key, value) {
  const response = await fetch('/api/v1/settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ key, value })
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.message || 'Failed to save settings.');
  }

  if (window.librarySettings) {
    window.librarySettings[key] = result.data?.[key] ?? value;
  }

  return result;
}

function saveButtonState(saving) {
  const button = document.getElementById('save-settings');

  if (!button) return;

  button.disabled = saving;

  button.innerHTML = saving
    ? `
      <span class="spinner-border spinner-border-sm me-1"></span>
      Saving...
    `
    : `
      <i class="ti ti-device-floppy me-1"></i>
      Save settings
    `;
}

function saveOverlaySettings() {
  const selected = Array.from(document.querySelectorAll('.settings-overlay-toggle:checked')).map(
    input => input.dataset.settingValue
  );

  if (!selected.length) {
    window.showLibraryNotification?.('Select at least one overlay item.', 'warning');

    renderSettingsPanel();
    return;
  }

  sessionStorage.setItem(OVERLAY_STORAGE_KEY, JSON.stringify(selected));

  window.showLibraryNotification?.('Card overlay settings updated.', 'success');

  document.dispatchEvent(
    new CustomEvent('library:overlay-settings-changed', {
      detail: { selected }
    })
  );
}

export function initSettingsPanel() {
  const panel = document.getElementById('library-settings-panel');

  if (!panel) return;

  panel.addEventListener('show.bs.offcanvas', () => {
    renderSettingsPanel();
  });

  renderSettingsPanel();

  const button = document.querySelector('[data-bs-target="#library-settings-panel"]');

  if (!button || button.dataset.settingsBound === 'true') return;

  button.dataset.settingsBound = 'true';

  button.addEventListener('click', () => {
    renderSettingsPanel();
  });
}
