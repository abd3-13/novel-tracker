import { getSyncRegistry, runSync } from './../api.js';

// Global state
const syncConfig = {
  source: 'local',
  mode: 'fill_missing',
  dryRun: false,
  force: false
};

function updateSyncConfig() {
  syncConfig.source = document.querySelector('input[name="sync-source"]:checked').value;

  syncConfig.mode = document.getElementById('sync-mode').value;

  syncConfig.dryRun = document.getElementById('sync-dry-run').checked;
  syncConfig.force = document.getElementById('sync-force').checked;
}

export function initSyncPanel() {
  renderMetadata();

  updateSyncConfig();

  bindEvents();
}

let syncFields = [];

function isFieldDisabled(field, source) {
  return !field.providers.includes(source);
}

function renderPills() {
  const source = syncConfig.source;

  document.querySelectorAll('.sync-field').forEach(cb => {
    const field = syncFields.find(f => f.id === cb.value);
    const disabled = isFieldDisabled(field, source);

    cb.disabled = disabled;

    if (disabled) cb.checked = false;
  });

  updateMetadataToggle();
}

async function renderMetadata() {
  const container = document.getElementById('sync-metadata');

  container.innerHTML = `<div class="text-center py-4"><div class="spinner-border spinner-border-sm text-muted"></div></div>`;

  try {
    syncFields = await getSyncRegistry();
    const source = syncConfig.source;

    container.innerHTML = `
      <div class="form-selectgroup d-flex flex-wrap gap-0">
        ${syncFields
          .map(field => {
            const isdisabled = isFieldDisabled(field, source);
            return `
              <label class="form-selectgroup-item">
                <input type="checkbox" class="form-selectgroup-input sync-field" value="${field.id}" ${isdisabled ? 'disabled' : ''}>
                <span class="form-selectgroup-label d-flex align-items-center px-3"> <i class="ti ti-${field.icon} me-2"></i>${field.name}</span>
              </label>
            `;
          })
          .join('')}
      </div>
    `;
  } catch (err) {
    console.error(err);
    container.innerHTML = `<div class="alert alert-danger mb-0"><i class="ti ti-alert-circle me-2"></i>Failed to load synchronization metadata.</div>`;
  }
}

function bindEvents() {
  const offcanvas = document.getElementById('sync-offcanvas');

  offcanvas.querySelectorAll('input, select').forEach(el => el.addEventListener('change', updateSyncConfig));

  document.querySelectorAll('input[name="sync-source"]').forEach(el => el.addEventListener('change', onSourceChanged));

  document.getElementById('metadata-toggle').addEventListener('change', onMetadataToggle);

  document.getElementById('sync-metadata').addEventListener('change', updateMetadataToggle);

  document.getElementById('sync-start').addEventListener('click', startSync);
}

function onSourceChanged() {
  updateSyncConfig();
  renderPills();
}

function onMetadataToggle(e) {
  document.querySelectorAll('.sync-field:not(:disabled)').forEach(cb => (cb.checked = e.target.checked));

  updateMetadataToggle();
}

function updateMetadataToggle() {
  const enabled = document.querySelectorAll('.sync-field:not(:disabled)');
  const checked = document.querySelectorAll('.sync-field:not(:disabled):checked');

  const toggle = document.getElementById('metadata-toggle');
  const icon = document.getElementById('metadata-toggle-icon');

  const allSelected = enabled.length && enabled.length === checked.length;

  toggle.checked = allSelected;

  icon.className = allSelected ? 'ti ti-deselect text-primary' : 'ti ti-select-all';
}

function collectJob() {
  return {
    source: syncConfig.source,

    mode: syncConfig.mode,

    dry_run: syncConfig.dryRun,

    force: syncConfig.force,
    // TODO: add ui selection mode so novels can be id of the selected librray
    novels: [13],

    fields: Array.from(document.querySelectorAll('.sync-field:checked')).map(cb => cb.value)
  };
}

async function startSync() {
  const job = collectJob();

  try {
    const result = await runSync(job);

    console.log(result);
  } catch (err) {
    console.error(err);
  }
}
