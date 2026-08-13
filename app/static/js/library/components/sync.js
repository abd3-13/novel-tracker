import { library } from '../state.js';
import { getSyncRegistry, runSync, listenSyncProgress } from './../api.js';
import { showNotification } from './../../notifi.js';
// Global state
const syncConfig = {
  source: 'local',
  mode: 'fill_missing',
  dryRun: false,
  force: false,
  ids: []
};

const syncProgress = {
  total: 0,
  updated: 0,
  skipped: 0,
  warnings: 0,
  errors: 0
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

function resetSyncPanel() {
  // Reset runtime state
  resetSyncProgress();

  // Reset progress UI
  updateSyncProgress(0, 0);

  document.getElementById('sync-current-novel').textContent = 'Waiting...';
  document.getElementById('sync-current-status').textContent = 'Preparing synchronization';

  // Reset stages
  updateSyncStage(null);

  // Clear result state
  document.getElementById('sync-result-title').textContent = 'Synchronization Complete';

  document.getElementById('sync-result-message').textContent = 'Synchronization finished.';

  document.getElementById('sync-result-problem-list').innerHTML = '';

  document.getElementById('sync-result-problems').classList.add('d-none');

  // Reset result counters
  document.getElementById('sync-result-total').textContent = '0';
  document.getElementById('sync-result-updated').textContent = '0';
  document.getElementById('sync-result-skipped').textContent = '0';
  document.getElementById('sync-result-errors').textContent = '0';

  // Reset button
  setSyncButtonState('idle');

  // Return to configuration view
  showSyncView('config');
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

function showSyncView(view) {
  const views = {
    config: 'sync-config-view',
    progress: 'sync-progress-view',
    result: 'sync-result-view'
  };

  const footers = {
    config: 'sync-config-footer',
    progress: 'sync-progress-footer',
    result: 'sync-result-footer'
  };

  Object.values(views).forEach(id => {
    document.getElementById(id)?.classList.add('d-none');
  });

  Object.values(footers).forEach(id => {
    document.getElementById(id)?.classList.add('d-none');
  });

  document.getElementById(views[view])?.classList.remove('d-none');

  document.getElementById(footers[view])?.classList.remove('d-none');
}

function updateSyncStage(stage) {
  const stages = ['providers', 'metadata', 'commit', 'done'];
  const currentIndex = stages.indexOf(stage);

  document.querySelectorAll('#sync-stages [data-stage]').forEach(element => {
    const name = element.dataset.stage;
    const index = stages.indexOf(name);
    const icon = element.querySelector('i');

    element.classList.remove('text-primary', 'text-success', 'text-muted');

    if (stage === null) {
      icon.className = 'ti ti-circle me-2';
      element.classList.add('text-muted');
    } else if (index < currentIndex) {
      icon.className = 'ti ti-check me-2';
      element.classList.add('text-success');
    } else if (index === currentIndex) {
      icon.className = 'ti ti-loader-2 me-2';
      element.classList.add('text-primary');
    } else {
      icon.className = 'ti ti-circle me-2';
      element.classList.add('text-muted');
    }
  });
}

function updateCurrentNovel(novel) {
  document.getElementById('sync-current-novel').textContent = novel;

  document.getElementById('sync-current-status').textContent = 'Synchronizing...';
}

function finishCurrentNovel(result) {
  const status = document.getElementById('sync-current-status');

  if (result.errors?.length) {
    status.textContent = 'Completed with errors';
  } else if (result.warnings?.length) {
    status.textContent = 'Completed with warnings';
  } else if (result.updated) {
    status.textContent = 'Updated';
  } else {
    status.textContent = 'Skipped';
  }
}

function updateSyncProgress(current, total) {
  const percent = total ? Math.round((current / total) * 100) : 0;

  document.getElementById('sync-progress-count').textContent = `${current} / ${total}`;

  document.getElementById('sync-progress-percent').textContent = `${percent}%`;

  document.getElementById('sync-progress-bar').style.width = `${percent}%`;
}

function updateSyncCounters() {
  document.getElementById('sync-count-updated').textContent = syncProgress.updated;

  document.getElementById('sync-count-skipped').textContent = syncProgress.skipped;

  document.getElementById('sync-count-warnings').textContent = syncProgress.warnings;

  document.getElementById('sync-count-errors').textContent = syncProgress.errors;
}

function resetSyncProgress() {
  syncProgress.total = 0;
  syncProgress.updated = 0;
  syncProgress.skipped = 0;
  syncProgress.warnings = 0;
  syncProgress.errors = 0;

  updateSyncCounters();
}

function processNovelResult(result) {
  if (result.updated) {
    syncProgress.updated++;
  } else if (!result.errors?.length) {
    syncProgress.skipped++;
  }

  syncProgress.warnings += result.warnings?.length || 0;
  syncProgress.errors += result.errors?.length || 0;

  updateSyncCounters();
}
function renderSyncProblems(results) {
  const container = document.getElementById('sync-result-problem-list');
  const section = document.getElementById('sync-result-problems');

  container.innerHTML = '';

  const problems = [];

  results.forEach(result => {
    for (const error of result.errors || []) {
      problems.push({
        type: 'error',
        title: result.title || 'Unknown novel',
        message: error
      });
    }

    for (const warning of result.warnings || []) {
      problems.push({
        type: 'warning',
        title: result.title || 'Unknown novel',
        message: warning
      });
    }
  });

  if (!problems.length) {
    section.classList.add('d-none');
    return;
  }

  section.classList.remove('d-none');

  for (const problem of problems) {
    const isError = problem.type === 'error';
    const icon = isError ? 'alert-circle' : 'alert-triangle';
    const css = isError ? 'text-danger' : 'text-warning';

    const item = document.createElement('div');

    item.className = 'list-group-item py-2 px-3';

    item.innerHTML = `
      <div class="d-flex align-items-start gap-2">
        <i class="ti ti-${icon} ${css} mt-1 flex-shrink-0"></i>

        <div class="min-width-0 flex-fill">
          <div class="fw-semibold text-truncate" title="${problem.title}">
            ${problem.title}
          </div>

          <div class="text-muted small text-break">
            ${problem.message}
          </div>
        </div>
      </div>
    `;

    container.appendChild(item);
  }
}
function handleSyncEvent(event, data) {
  switch (event) {
    case 'job_start':
      showSyncView('progress');
      handleJobStart(data);
      break;

    case 'novel_start':
      handleNovelStart(data);
      break;

    case 'stage':
      handleStage(data);
      break;

    case 'field':
      handleField(data);
      break;

    case 'novel_finish':
      handleNovelFinish(data);
      break;

    case 'job_finish':
      handleJobFinish(data);
      break;
  }
}

function handleJobStart(data) {
  syncProgress.total = data.total || 0;

  updateSyncProgress(0, syncProgress.total);
  updateSyncCounters();

  document.getElementById('sync-current-novel').textContent = 'Preparing synchronization...';

  document.getElementById('sync-current-status').textContent = `${syncProgress.total} novel(s) selected`;

  updateSyncStage('providers');
}

function handleNovelStart(data) {
  updateCurrentNovel(data.novel);

  updateSyncProgress(data.current - 1, data.total);

  updateSyncStage('providers');
}

function handleStage(data) {
  updateSyncStage(data.stage);
}

function handleField(data) {
  const status = document.getElementById('sync-current-status');

  if (!status) return;

  status.textContent = `Synchronizing ${data.name || data.field}...`;
}

function handleNovelFinish(data) {
  const result = data.result;

  finishCurrentNovel(result);
  processNovelResult(result);

  updateSyncProgress(data.current, data.total);
}

function handleJobFinish(data) {
  console.log('JOB FINISH:', data);

  // Make sure progress is visually complete.
  updateSyncProgress(data.summary.total, data.summary.total);

  // Final result screen.
  renderSyncResult(data);
}

function bindEvents() {
  const offcanvas = document.getElementById('sync-offcanvas');

  offcanvas.querySelectorAll('input, select').forEach(el => el.addEventListener('change', updateSyncConfig));

  document.querySelectorAll('input[name="sync-source"]').forEach(el => el.addEventListener('change', onSourceChanged));

  document.getElementById('metadata-toggle').addEventListener('change', onMetadataToggle);

  document.getElementById('sync-metadata').addEventListener('change', updateMetadataToggle);

  document.getElementById('sync-start').addEventListener('click', startSync);
  document.getElementById('sync-done').addEventListener('click', resetSyncPanel);
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

  resetSyncProgress();

  showSyncView('progress');

  const job = collectJob();

  try {
    const result = await runSync(job);

    const jobId = result.job_id;

    console.log('Synchronization started:', jobId);

    listenSyncProgress(jobId, {
      job_start(data) {
        handleSyncEvent('job_start', data);
      },

      novel_start(data) {
        handleSyncEvent('novel_start', data);
      },

      stage(data) {
        handleSyncEvent('stage', data);
      },

      field(data) {
        handleSyncEvent('field', data);
      },

      novel_finish(data) {
        handleSyncEvent('novel_finish', data);
      },

      job_finish(data) {
        handleSyncEvent('job_finish', data);
      },

      error(error) {
        console.error('SYNC ERROR:', error);

        showNotification('Synchronization event stream failed.', 'error');

        setSyncButtonState('error');
      }
    });
  } catch (err) {
    console.error(err);

    showNotification(err.message || 'Synchronization failed.', 'error');

    setSyncButtonState('error');
  }
}

function renderSyncResult(data) {
  const summary = data.summary;
  const results = data.results || [];

  console.log('SYNC DONE:', summary);

  // Final counters
  document.getElementById('sync-result-total').textContent = summary.total;

  document.getElementById('sync-result-updated').textContent = summary.updated;

  document.getElementById('sync-result-skipped').textContent = summary.skipped;

  document.getElementById('sync-result-errors').textContent = summary.errors;

  renderSyncProblems(results);

  const title = document.getElementById('sync-result-title');
  const message = document.getElementById('sync-result-message');
  const icon = document.getElementById('sync-result-icon');

  if (summary.errors > 0) {
    title.textContent = 'Synchronization Completed with Errors';
    message.textContent = `${summary.errors} novel(s) encountered errors.`;

    icon.className = 'ti ti-alert-circle fs-1';
  } else if (summary.warnings > 0) {
    title.textContent = 'Synchronization Completed with Warnings';
    message.textContent = `${summary.warnings} warning(s) were reported.`;

    icon.className = 'ti ti-alert-triangle fs-1';
  } else {
    title.textContent = 'Synchronization Complete';
    message.textContent = 'All selected novels were synchronized successfully.';

    icon.className = 'ti ti-check fs-1';
  }

  showSyncView('result');

  if (summary.errors > 0) {
    setSyncButtonState('error');

    showNotification(`Synchronization completed with ${summary.errors} error(s).`, 'error');
  } else if (summary.warnings > 0) {
    setSyncButtonState('success');

    showNotification(`Synchronization completed with ${summary.warnings} warning(s).`, 'warning');
  } else {
    setSyncButtonState('success');

    showNotification('Synchronization completed successfully.', 'success');
  }
}
