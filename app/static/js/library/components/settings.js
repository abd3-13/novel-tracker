const OVERLAY_METADATA_OPTIONS = [
  { id: 'characters', label: 'Characters', icon: 'users' },
  { id: 'progress', label: 'Read progress', icon: 'percentage' },
  { id: 'chapter', label: 'Current chapter', icon: 'bookmark' },
  { id: 'updates', label: 'New chapters', icon: 'bookmarks' },
  { id: 'time', label: 'Last update', icon: 'clock' }
];

function parseOverlayMetadata(rawValue) {
  const fallback = ['characters', 'progress', 'chapter', 'updates', 'time'];

  if (!rawValue) return fallback;

  try {
    const parsed = JSON.parse(rawValue);
    return Array.isArray(parsed) && parsed.length ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function getSelectedOverlayMetadata() {
  const settings = window.librarySettings || {};
  return parseOverlayMetadata(settings.CARD_OVERLAY_METADATA || settings.card_overlay_metadata);
}

export function renderSettingsPanel() {
  const settings = window.librarySettings || {};
  const selected = new Set(getSelectedOverlayMetadata());

  const databaseRows = Object.entries(settings)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => {
      const normalized = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
      return `
        <div class="mb-3">
          <label class="form-label small text-uppercase text-muted mb-1">${key}</label>
          <input type="text" class="form-control form-control-sm settings-db-field" data-setting-key="${key}" value="${String(normalized).replace(/"/g, '&quot;')}" />
        </div>
      `;
    })
    .join('');

  const overlayRows = OVERLAY_METADATA_OPTIONS.map(
    option => `
    <label class="form-check mb-2">
      <input class="form-check-input settings-overlay-toggle" type="checkbox" data-setting-value="${option.id}" ${selected.has(option.id) ? 'checked' : ''} />
      <span class="form-check-label d-flex align-items-center gap-2">
        <i class="ti ti-${option.icon}"></i>
        ${option.label}
      </span>
    </label>
  `
  ).join('');

  document.getElementById('library-settings-content').innerHTML = `
    <div class="d-flex flex-column gap-3">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title mb-0">Database settings</h3>
        </div>
        <div class="card-body">
          <div class="mb-3">
            ${databaseRows || '<div class="text-muted">No settings available.</div>'}
          </div>
          <button type="button" class="btn btn-primary" id="save-database-settings">
            <i class="ti ti-device-floppy me-1"></i>
            Save database settings
          </button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title mb-0">Card overlay metadata</h3>
        </div>
        <div class="card-body">
          <div class="text-secondary small mb-3">Choose which metadata appears on each novel card overlay.</div>
          ${overlayRows}
          <button type="button" class="btn btn-primary mt-3" id="save-overlay-settings">
            <i class="ti ti-device-floppy me-1"></i>
            Save overlay settings
          </button>
        </div>
      </div>
    </div>
  `;

  const saveDatabaseButton = document.getElementById('save-database-settings');
  if (saveDatabaseButton) {
    saveDatabaseButton.addEventListener('click', async () => {
      const inputs = document.querySelectorAll('.settings-db-field');
      const updates = [];

      inputs.forEach(input => {
        const key = input.dataset.settingKey;
        const value = input.value;
        if (key) updates.push({ key, value });
      });

      for (const item of updates) {
        await saveSetting(item.key, item.value);
      }

      if (window.showLibraryNotification) {
        window.showLibraryNotification('Database settings saved.', 'success');
      }
    });
  }

  const saveOverlayButton = document.getElementById('save-overlay-settings');
  if (saveOverlayButton) {
    saveOverlayButton.addEventListener('click', async () => {
      const selected = Array.from(document.querySelectorAll('.settings-overlay-toggle:checked')).map(
        el => el.dataset.settingValue
      );
      await saveSetting('CARD_OVERLAY_METADATA', selected);
      window.librarySettings = { ...window.librarySettings, CARD_OVERLAY_METADATA: JSON.stringify(selected) };
      if (window.showLibraryNotification) {
        window.showLibraryNotification('Card overlay metadata saved.', 'success');
      }
    });
  }
}

export async function saveSetting(key, value) {
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
