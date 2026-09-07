import { library } from '../state.js';
import { getSyncRegistry, runSync, cancelSync, listenSyncProgress } from './../api.js';
import { showNotification } from './../../notifi.js';
import { SYNC_TEXT, SYNC_BUTTON_STATES, SYNC_CANCEL_BUTTON_STATES } from './../config.js';
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

const syncLog = {
  maxEntries: 500,
  entries: []
};

let syncProblemsForDownload = [];
let syncJobId = null;
let syncEventSource = null;
let syncCancellationRequested = false;

function updateSyncConfig() {
  syncConfig.source = document.querySelector('input[name="sync-source"]:checked').value;

  syncConfig.mode = document.getElementById('sync-mode').value;

  syncConfig.dryRun = document.getElementById('sync-dry-run').checked;
  syncConfig.force = document.getElementById('sync-force').checked;
}

export function openNovelSync(id) {
  syncConfig.ids = [Number(id)];

  resetSyncPanel();

  const offcanvas = document.getElementById('sync-offcanvas');

  if (!offcanvas) return;
}

export function initSyncPanel(library) {
  renderMetadata();

  updateSyncConfig(library);

  bindEvents();
}

function resetSyncPanel() {
  syncEventSource?.close();
  syncEventSource = null;
  syncJobId = null;
  syncCancellationRequested = false;

  // Reset runtime state
  resetSyncProgress();

  // Reset Logs viewer
  resetSyncLog();

  // Reset progress UI
  updateSyncProgress(0, 0);

  document.getElementById('sync-current-novel').textContent = SYNC_TEXT.waiting;
  document.getElementById('sync-current-status').textContent = SYNC_TEXT.preparing;

  // Reset stages
  updateSyncStage(null);

  // Clear result state
  document.getElementById('sync-result-title').textContent = SYNC_TEXT.complete;

  document.getElementById('sync-result-message').textContent = SYNC_TEXT.finished;

  document.getElementById('sync-result-problem-list').innerHTML = '';

  syncProblemsForDownload = [];
  const downloadButton = document.getElementById('sync-download-problems');
  if (downloadButton) {
    downloadButton.classList.add('d-none');
  }

  document.getElementById('sync-result-problems').classList.add('d-none');

  // Reset result counters
  document.getElementById('sync-result-total').textContent = '0';
  document.getElementById('sync-result-updated').textContent = '0';
  document.getElementById('sync-result-skipped').textContent = '0';
  document.getElementById('sync-result-errors').textContent = '0';

  // Reset button
  setSyncButtonState('idle');
  setSyncCancelButtonState('idle');

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
  const status = document.getElementById('sync-current-status');

  if (!status || !stage) return;

  const labels = {
    providers: SYNC_TEXT.fetching,
    metadata: SYNC_TEXT.metadata,
    commit: 'Saving changes...',
    done: SYNC_TEXT.done
  };

  status.textContent = labels[stage] || stage;
}

function updateCurrentNovel(novel) {
  document.getElementById('sync-current-novel').textContent = novel;

  document.getElementById('sync-current-status').textContent = `${SYNC_TEXT.synchronizing} `;
}

function finishCurrentNovel(result) {
  const status = document.getElementById('sync-current-status');

  if (result.errors?.length) {
    status.textContent = SYNC_TEXT.completedWithErrors;
  } else if (result.warnings?.length) {
    status.textContent = SYNC_TEXT.completedWithWarnings;
  } else if (result.updated) {
    status.textContent = SYNC_TEXT.updated;
  } else {
    status.textContent = SYNC_TEXT.skipped;
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

function resetSyncLog() {
  syncLog.entries = [];

  const list = document.getElementById('sync-log-list');

  if (list) {
    list.innerHTML = '';
  }

  document.getElementById('sync-live-log')?.classList.add('d-none');
}

function addSyncLog(message, type = 'info') {
  const container = document.getElementById('sync-live-log');
  const list = document.getElementById('sync-log-list');

  if (!container || !list) return;

  container.classList.remove('d-none');

  syncLog.entries.push({
    time: new Date(),
    message,
    type
  });

  if (syncLog.entries.length > syncLog.maxEntries) {
    syncLog.entries.shift();
  }

  const row = document.createElement('div');
  row.className = 'sync-log-entry font-monospace small';

  const time = document.createElement('span');
  time.className = 'text-secondary';
  time.textContent = new Date().toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  const text = document.createElement('span');

  text.className = `ms-2 ${
    {
      info: 'text-muted',
      success: 'text-success',
      warning: 'text-warning',
      error: 'text-danger'
    }[type] || 'text-muted'
  }`;

  text.textContent = message;

  row.append(time, text);
  list.appendChild(row);

  const scrollContainer = document.getElementById('sync-log-container');

  if (scrollContainer) {
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }
}

function logNovelProblems(result) {
  for (const warning of result.warnings || []) {
    addSyncLog(`  ⚠ ${warning}`, 'warning');
  }

  for (const error of result.errors || []) {
    addSyncLog(`  ✖ ${error}`, 'error');
  }
}

function formatSyncIssueFilename() {
  const now = new Date();
  const stamp = [
    now.getFullYear().toString().slice(-2),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
    '-',
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
    String(now.getSeconds()).padStart(2, '0')
  ].join('');

  return `novel_sync_issues_${stamp}.txt`;
}

function downloadSyncProblems() {
  if (!syncProblemsForDownload.length) return;

  const lines = syncProblemsForDownload.map(problem => {
    const label = problem.type === 'error' ? 'ERROR' : 'WARNING';
    return `${label} | ${problem.title} | ${problem.message}`;
  });

  const content = `${lines.join('\n')}\n`;
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = formatSyncIssueFilename();
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
  showNotification('Synchronization issues downloaded.', 'success');
}

function renderSyncProblems(results) {
  const container = document.getElementById('sync-result-problem-list');
  const section = document.getElementById('sync-result-problems');
  const downloadButton = document.getElementById('sync-download-problems');

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

  syncProblemsForDownload = problems;

  if (!problems.length) {
    section.classList.add('d-none');
    if (downloadButton) {
      downloadButton.classList.add('d-none');
    }
    return;
  }

  section.classList.remove('d-none');

  if (downloadButton) {
    downloadButton.classList.remove('d-none');
  }

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

  addSyncLog(`Synchronization started — ${syncProgress.total} novel(s) selected.`, 'info');
}

function handleNovelStart(data) {
  updateCurrentNovel(data.novel);

  updateSyncProgress(data.current - 1, data.total);

  updateSyncStage('providers');
  addSyncLog(`[${data.current}/${data.total}] ${data.novel}`, 'info');
}

function handleStage(data) {
  updateSyncStage(data.stage);
  addSyncLog(`Stage: ${data.stage}`, 'info');
}

function handleField(data) {
  const status = document.getElementById('sync-current-status');

  if (!status) return;

  const name = data.name || data.field;
  const update = data.should_update ? data.value : 'no updates';

  status.textContent = `Synchronizing ${name}...`;
  addSyncLog(`  ↳ ${name} : ${update}`, 'info');
}

function handleNovelFinish(data) {
  const result = data.result;

  finishCurrentNovel(result);
  processNovelResult(result);

  updateSyncProgress(data.current, data.total);

  logNovelProblems(result);

  let type = 'success';
  let message = `[${data.current}/${data.total}] ${result.title}`;

  if (result.errors?.length) {
    type = 'error';
    message += ` — completed with ${result.errors.length} error(s)`;
  } else if (result.warnings?.length) {
    type = 'warning';
    message += ` — completed with ${result.warnings.length} warning(s)`;
  } else if (result.updated) {
    message += ' — updated';
  } else {
    message += ' — skipped';
  }

  addSyncLog(message, type);
}

function handleJobFinish(data) {
  const summary = data.summary;
  addSyncLog(
    `Synchronization finished — ${summary.total} processed, ` + `${summary.updated} updated, ` + `${summary.skipped} skipped, ` + `${summary.errors} error(s).`,
    summary.errors > 0 ? 'error' : summary.warnings > 0 ? 'warning' : 'success'
  );
  // Make sure progress is visually complete.
  updateSyncProgress(summary.total, summary.total);

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
  document.getElementById('sync-cancel').addEventListener('click', cancelCurrentSync);
  document.getElementById('sync-done').addEventListener('click', resetSyncPanel);
  document.getElementById('sync-download-problems').addEventListener('click', downloadSyncProblems);
  document.getElementById('sync-log-clear').addEventListener('click', () => {
    const list = document.getElementById('sync-log-list');

    if (list) {
      list.innerHTML = '';
    }

    syncLog.entries = [];
  });
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
  const config = SYNC_BUTTON_STATES[state] || SYNC_BUTTON_STATES.idle;

  button.disabled = config.disabled;
  button.innerHTML = config.html;
}

function setSyncCancelButtonState(state) {
  const button = document.getElementById('sync-cancel');
  const config = SYNC_CANCEL_BUTTON_STATES[state] || SYNC_CANCEL_BUTTON_STATES.idle;

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

    novels: syncConfig.ids.length ? [...syncConfig.ids] : [...library.ids]
  };
}

async function startSync() {
  setSyncButtonState('loading');
  setSyncCancelButtonState('idle');

  syncJobId = null;
  syncCancellationRequested = false;

  resetSyncProgress();
  resetSyncLog();

  showSyncView('progress');

  const job = collectJob();

  try {
    const result = await runSync(job);

    syncJobId = result.job_id;

    //console.log('Synchronization started:', syncJobId);

    syncEventSource = listenSyncProgress(syncJobId, {
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
        syncEventSource = null;
        syncJobId = null;
      },

      error(error) {
        console.error('SYNC ERROR:', error);

        showNotification('Synchronization event stream failed.', 'error');
        syncEventSource = null;
        syncJobId = null;

        setSyncButtonState('error');
        setSyncCancelButtonState('done');
      }
    });
  } catch (err) {
    console.error(err);

    showNotification(err.message || 'Synchronization failed.', 'error');

    setSyncButtonState('error');
    setSyncCancelButtonState('done');
  }
}

async function cancelCurrentSync() {
  if (!syncJobId || syncCancellationRequested) return;

  syncCancellationRequested = true;
  setSyncCancelButtonState('cancelling');

  const status = document.getElementById('sync-current-status');
  if (status) status.textContent = 'Cancellation requested...';

  addSyncLog('Cancellation requested. Finishing the current operation...', 'warning');

  try {
    await cancelSync(syncJobId);
    showNotification('Synchronization cancellation requested.', 'warning');
  } catch (err) {
    console.error(err);

    syncCancellationRequested = false;
    setSyncCancelButtonState('idle');
    showNotification(err.message || 'Failed to cancel synchronization.', 'error');
  }
}

function renderSyncResult(data) {
  const summary = data.summary;
  const results = data.results || [];

  //console.log('SYNC DONE:', summary);

  // Final counters
  document.getElementById('sync-result-total').textContent = summary.total;

  document.getElementById('sync-result-updated').textContent = summary.updated;

  document.getElementById('sync-result-skipped').textContent = summary.skipped;

  document.getElementById('sync-result-errors').textContent = summary.errors;

  renderSyncProblems(results);

  const title = document.getElementById('sync-result-title');
  const message = document.getElementById('sync-result-message');
  const icon = document.getElementById('sync-result-icon');

  if (summary.cancelled) {
    title.textContent = 'Synchronization Cancelled';
    message.textContent = `${summary.total} novel(s) were processed before cancellation.`;

    icon.className = 'ti ti-cancel fs-1';
    icon.parentElement.className = 'avatar avatar-xl bg-warning-lt mb-3';
  } else if (summary.errors > 0) {
    title.textContent = 'Synchronization Completed with Errors';
    message.textContent = `${summary.errors} novel(s) encountered errors.`;

    icon.className = 'ti ti-alert-circle fs-1';
    icon.parentElement.className = 'avatar avatar-xl bg-danger-lt mb-3';
  } else if (summary.warnings > 0) {
    title.textContent = 'Synchronization Completed with Warnings';
    message.textContent = `${summary.warnings} warning(s) were reported.`;

    icon.className = 'ti ti-alert-triangle fs-1';
    icon.parentElement.className = 'avatar avatar-xl bg-warning-lt mb-3';
  } else {
    title.textContent = 'Synchronization Complete';
    message.textContent = 'All selected novels were synchronized successfully.';

    icon.className = 'ti ti-check fs-1';
    icon.parentElement.className = 'avatar avatar-xl bg-success-lt mb-3';
  }

  showSyncView('result');
  setSyncCancelButtonState(summary.cancelled ? 'done' : 'done');

  if (summary.cancelled) {
    setSyncButtonState('error');
    showNotification('Synchronization cancelled.', 'warning');
  } else if (summary.errors > 0) {
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
