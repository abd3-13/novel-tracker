import { library } from '../state.js';
import { getSyncRegistry, runSync } from './../api.js';
import { showNotification } from './../../notifi.js';
// Global state
const syncConfig = {
  source: 'local',
  mode: 'fill_missing',
  dryRun: false,
  force: false,
  ids: []
};

function updateSyncConfig() {
  syncConfig.source = document.querySelector('input[name="sync-source"]:checked').value;

  syncConfig.mode = document.getElementById('sync-mode').value;

  syncConfig.dryRun = document.getElementById('sync-dry-run').checked;
  syncConfig.force = document.getElementById('sync-force').checked;
}

export function initSyncPanel(library) {
  renderMetadata();

  updateSyncConfig(library);

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
  reorderPills();
  updateMetadataToggle();
}

function reorderPills() {
  const group = document.querySelector('#sync-metadata .form-selectgroup');

  const enabled = [];
  const disabled = [];

  for (const item of group.children) {
    const cb = item.querySelector('.sync-field');
    (cb.disabled ? disabled : enabled).push(item);
  }

  [...enabled, ...disabled].forEach(item => group.appendChild(item));
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
    reorderPills();
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

function setSyncButtonState(state) {
  const button = document.getElementById('sync-start');

  const states = {
    idle: {
      disabled: false,
      html: '<i class="ti ti-refresh me-1"></i> Synchronize'
    },

    loading: {
      disabled: true,
      html: '<span class="spinner-border spinner-border-sm me-1"></span> Synchronizing...'
    },

    success: {
      disabled: true,
      html: '<i class="ti ti-check me-1"></i> Synchronized'
    },

    error: {
      disabled: true,
      html: '<i class="ti ti-alert-circle me-1"></i> Failed'
    }
  };

  const config = states[state];

  button.disabled = config.disabled;
  button.innerHTML = config.html;
}

function collectJob() {
  return {
    source: syncConfig.source,

    mode: syncConfig.mode,

    dry_run: syncConfig.dryRun,

    force: syncConfig.force,

    fields: Array.from(document.querySelectorAll('.sync-field:checked')).map(cb => cb.value),

    novels: [...library.ids]
  };
}

async function startSync() {
  setSyncButtonState('loading');

  const job = collectJob();

  try {
    const result = await runSync(job);

    console.log('Sync result:', result);

    if (result.category === 'error') {
      const errors = result.results.flatMap(result =>
        (result.errors || []).map(error => ({ title: result.title, message: error }))
      );
      const errorMessage = errors.map(error => `${error.title}: ${error.message}`).join('\n');

      console.error('Synchronization errors:', errorMessage);

      showNotification(result.message, 'error');

      setSyncButtonState('error');
    } else if (result.category === 'warning') {
      showNotification(result.message, 'warning');

      setSyncButtonState('success');
    } else {
      showNotification(result.message, 'success');

      setSyncButtonState('success');
    }
  } catch (err) {
    console.error('Synchronization failed:', err);

    showNotification(err.message || 'Synchronization failed.', 'error');

    setSyncButtonState('error');
  }

  setTimeout(() => {
    setSyncButtonState('idle');
  }, 2000);
}
