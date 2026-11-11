import { escapeHtml } from './../utils.js';
import { listenImportScan, streamImport } from './../api.js';
import { IMPORT_TEXT } from './../config.js';
import { buildImportDetail, getSelectedImportMetadataDefinitions } from './import-metadata.js';

const VIEWS = {
  config: 'import-config-view',
  scanning: 'import-scanning-view',
  results: 'import-results-view',
  progress: 'import-progress-view',
  result: 'import-result-view'
};

const FOOTERS = {
  config: 'import-config-footer',
  results: 'import-results-footer',
  progress: 'import-progress-footer',
  result: 'import-result-footer'
};

const state = {
  candidates: [],
  selected: new Set(),
  scanSource: null,
  scanTimer: null,
  scanStartedAt: 0
};

function setView(name) {
  Object.entries(VIEWS).forEach(([key, id]) => {
    document.getElementById(id)?.classList.toggle('d-none', key !== name);
  });

  const footer = FOOTERS[name] || null;

  Object.values(FOOTERS).forEach(id => {
    document.getElementById(id)?.classList.toggle('d-none', id !== footer);
  });
}

function setDirectory(path) {
  const directory = document.getElementById('import-directory');

  if (directory) {
    directory.textContent = path || window.librarySettings?.LOCAL_EPUB_DIR || 'Not configured';
  }
}

function selectableCandidates() {
  return state.candidates.filter(candidate => candidate.status === 'new');
}

function updateSelectionUI() {
  const selectable = selectableCandidates();
  const total = selectable.length;
  const selected = state.selected.size;

  const selectAll = document.getElementById('import-select-all');

  if (selectAll) {
    selectAll.checked = total > 0 && selected === total;
    selectAll.indeterminate = selected > 0 && selected < total;
    selectAll.disabled = total === 0;
  }

  document.querySelectorAll('.import-candidate-check').forEach(input => {
    input.checked = state.selected.has(input.dataset.filename);
  });

  const button = document.getElementById('import-submit');

  if (!button) return;

  if (selected === 0) {
    button.disabled = true;
    button.textContent = `${IMPORT_TEXT.import} (0)`;
    return;
  }

  button.disabled = false;

  if (selected === total) {
    button.innerHTML = `<i class="ti ti-download me-1"></i>${IMPORT_TEXT.importAll} (${total})`;
  } else {
    button.innerHTML = `<i class="ti ti-download me-1"></i>${IMPORT_TEXT.import} (${selected})`;
  }
}

function candidateRow(candidate, detailDefinitions) {
  const isNew = candidate.status === 'new';

  const badgeStyles = {
    new: { className: 'bg-blue-lt', label: IMPORT_TEXT.new },
    already_exists: { className: 'bg-yellow-lt', label: IMPORT_TEXT.alreadyExists },
    error: { className: 'bg-red-lt', label: IMPORT_TEXT.error }
  };

  const badge = badgeStyles[candidate.status] || badgeStyles.error;
  const cover = `/api/v1/import/cover?filename=${encodeURIComponent(candidate.filename)}`;
  const metadata = buildImportDetail(candidate, detailDefinitions);

  return `
    <div class="list-group-item ${isNew ? '' : 'opacity-75'}">
      <div class="d-flex align-items-center gap-3">
        <input
          class="form-check-input import-candidate-check"
          type="checkbox"
          data-filename="${escapeHtml(candidate.filename)}"
          ${isNew ? '' : 'disabled'}
        />
        <img
          class="import-cover rounded"
          src="${cover}"
          alt=""
          loading="lazy"
          onerror="this.onerror=null;this.src='/static/img/cover/cover.webp'"
        />
        <div class="flex-fill min-width-0">
          <div class="fw-bold text-truncate">${escapeHtml(candidate.title || candidate.filename)}</div>
          ${metadata ? `<div class="text-muted small text-truncate" title="${escapeHtml(metadata)}">${escapeHtml(metadata)}</div>` : ''}
          <div class="text-secondary small text-truncate">${escapeHtml(candidate.filename)}</div>
          ${candidate.reason ? `<div class="text-red small">${escapeHtml(candidate.reason)}</div>` : ''}
        </div>
        <span class="badge ${badge.className}">${badge.label}</span>
      </div>
    </div>
  `;
}

function renderCandidateList() {
  const definitions = getSelectedImportMetadataDefinitions();
  const list = document.getElementById('import-candidate-list');

  if (list) {
    list.innerHTML = state.candidates.map(candidate => candidateRow(candidate, definitions)).join('');
  }

  updateSelectionUI();
}

function renderCandidates(result) {
  const candidates = result.candidates || [];
  const counts = result.counts || {};

  state.candidates = candidates;
  state.selected = new Set(selectableCandidates().map(candidate => candidate.filename));

  setDirectory(result.directory);

  const summary = document.getElementById('import-results-summary');

  if (summary) {
    summary.textContent = `${counts.new || 0} new · ${counts.known || 0} already imported · ${counts.already_exists || 0} duplicate titles · ${counts.errors || 0} errors`;
  }

  const count = document.getElementById('import-results-count');

  if (count) {
    count.textContent = String(counts.new || 0);
  }

  document.getElementById('import-empty')?.classList.toggle('d-none', candidates.length > 0);
  document.getElementById('import-select-all-wrap')?.classList.toggle('d-none', !selectableCandidates().length);

  renderCandidateList();
}

function setText(id, text) {
  const element = document.getElementById(id);

  if (element) element.textContent = text;
}

function stopScan() {
  if (state.scanSource) {
    state.scanSource.close();
    state.scanSource = null;
  }

  if (state.scanTimer) {
    clearInterval(state.scanTimer);
    state.scanTimer = null;
  }

  const button = document.getElementById('import-scan');

  if (button) button.disabled = false;
}

function formatElapsed(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;

  return minutes ? `${minutes}m ${String(remainder).padStart(2, '0')}s` : `${seconds}s`;
}

function updateElapsed() {
  setText('import-scan-elapsed', formatElapsed(Date.now() - state.scanStartedAt));
}

function setScanBarIndeterminate() {
  const bar = document.getElementById('import-scan-progress');

  if (!bar) return;

  bar.classList.add('progress-bar-indeterminate');
  bar.style.width = '100%';
}

function setScanBarProgress(percent) {
  const bar = document.getElementById('import-scan-progress');

  if (!bar) return;

  bar.classList.remove('progress-bar-indeterminate');
  bar.style.width = `${percent}%`;
}

function resetScanProgress() {
  setText('import-scan-stage', 'Finding EPUB files...');
  setText('import-scan-detail', 'Looking inside the local EPUB directory.');
  setText('import-scan-count', '');
  setText('import-scan-percent', '');
  setText('import-scan-current', '');
  setText('import-scan-elapsed', '0s');

  document.getElementById('import-scan-current-card')?.classList.add('d-none');

  setScanBarIndeterminate();
}

function updateScanProgress(data) {
  if (data.stage === 'listing') {
    setText('import-scan-stage', 'Finding EPUB files...');
    setText('import-scan-detail', 'Looking inside the local EPUB directory.');
    setText('import-scan-count', '');
    setText('import-scan-percent', '');
    document.getElementById('import-scan-current-card')?.classList.add('d-none');
    setScanBarIndeterminate();
    return;
  }

  if (data.stage === 'checking') {
    setText('import-scan-stage', 'Checking library records...');
    setText('import-scan-detail', `${data.total || 0} EPUBs found · ${data.known || 0} already imported`);
    setText('import-scan-count', `${data.new || 0} new`);
    setText('import-scan-percent', '');
    document.getElementById('import-scan-current-card')?.classList.add('d-none');
    setScanBarIndeterminate();
    return;
  }

  if (data.stage === 'metadata') {
    const total = data.total || 0;
    const current = data.current || 0;
    const percent = total ? Math.round((current / total) * 100) : 0;

    const parts = [];

    if (data.new) parts.push(`${data.new} new`);
    if (data.already_exists) parts.push(`${data.already_exists} duplicate`);
    if (data.errors) parts.push(`${data.errors} errors`);

    setText('import-scan-stage', 'Reading metadata...');
    setText(
      'import-scan-detail',
      parts.length ? parts.join(' · ') : 'Extracting local metadata from new EPUBs.'
    );
    setText('import-scan-count', `${current} / ${total}`);
    setText('import-scan-percent', `${percent}%`);
    setText('import-scan-current', data.filename || '');
    document.getElementById('import-scan-current-card')?.classList.remove('d-none');
    setScanBarProgress(percent);
  }
}

function scan() {
  stopScan();

  const button = document.getElementById('import-scan');

  if (button) button.disabled = true;

  setView('scanning');
  resetScanProgress();

  state.scanStartedAt = Date.now();
  state.scanTimer = setInterval(updateElapsed, 1000);

  state.scanSource = listenImportScan({
    progress: updateScanProgress,
    done: result => {
      stopScan();
      renderCandidates(result);
      setView('results');
    },
    error: error => {
      stopScan();
      window.showLibraryNotification?.(error.message || IMPORT_TEXT.scanFailed, 'error');
      setView('config');
    }
  });
}

const importState = {
  controller: null,
  silentAbort: false,
  total: 0,
  imported: 0,
  skipped: 0,
  failed: 0,
  results: [],
  finalResult: null,
  streamError: null
};

const IMPORT_STAGE_LABELS = {
  metadata: 'Reading metadata...',
  cover: 'Extracting cover...',
  insert: 'Saving to library...'
};

function updateImportCounters() {
  setText('import-count-imported', String(importState.imported));
  setText('import-count-skipped', String(importState.skipped));
  setText('import-count-failed', String(importState.failed));
}

function updateImportProgress(current, total) {
  const percent = total ? Math.round((current / total) * 100) : 0;

  setText('import-progress-count', `${current} / ${total}`);
  setText('import-progress-percent', `${percent}%`);

  const bar = document.getElementById('import-progress-bar');

  if (bar) bar.style.width = `${percent}%`;
}

function resetImportProgress() {
  importState.total = 0;
  importState.imported = 0;
  importState.skipped = 0;
  importState.failed = 0;
  importState.results = [];
  importState.finalResult = null;
  importState.streamError = null;

  updateImportProgress(0, 0);
  updateImportCounters();

  setText('import-current-file', 'Waiting...');
  setText('import-current-status', 'Preparing import');
}

function resetImportLog() {
  const list = document.getElementById('import-log-list');

  if (list) list.innerHTML = '';

  document.getElementById('import-live-log')?.classList.add('d-none');
}

function addImportLog(message, type = 'info') {
  const container = document.getElementById('import-live-log');
  const list = document.getElementById('import-log-list');

  if (!container || !list) return;

  container.classList.remove('d-none');

  const row = document.createElement('div');
  row.className = 'font-monospace small';

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

  const scrollContainer = document.getElementById('import-log-container');

  if (scrollContainer) {
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }
}

function partialResult() {
  return {
    summary: {
      requested: importState.total,
      imported: importState.imported,
      skipped: importState.skipped,
      failed: importState.failed
    },
    results: importState.results
  };
}

function handleImportStart(data) {
  importState.total = data.total || 0;

  updateImportProgress(0, importState.total);
  updateImportCounters();

  setText('import-current-file', 'Preparing import...');
  setText('import-current-status', `${importState.total} EPUB(s) selected`);

  addImportLog(`Import started — ${importState.total} EPUB(s) selected.`, 'info');
}

function handleImportFileStart(data) {
  updateImportProgress((data.current || 1) - 1, data.total || 0);

  setText('import-current-file', data.filename || '');
  setText('import-current-status', 'Preparing import...');

  addImportLog(`[${data.current}/${data.total}] ${data.filename}`, 'info');
}

function handleImportStage(data) {
  const label = IMPORT_STAGE_LABELS[data.stage] || data.stage;

  setText('import-current-status', label);
  addImportLog(`  ↳ ${label}`, 'info');
}

function handleImportFileDone(data) {
  if (data.status === 'imported') {
    importState.imported += 1;
  } else if (data.status === 'skipped') {
    importState.skipped += 1;
  } else {
    importState.failed += 1;
  }

  importState.results.push({
    filename: data.filename,
    status: data.status,
    ...(data.reason ? { reason: data.reason } : {})
  });

  updateImportProgress(data.current || 0, data.total || 0);
  updateImportCounters();

  const title = data.title || data.filename;

  if (data.status === 'imported') {
    setText('import-current-file', title);
    setText('import-current-status', IMPORT_TEXT.imported);
    addImportLog(`  ✔ Imported — ${title}`, 'success');
  } else if (data.status === 'skipped') {
    setText('import-current-status', data.reason || IMPORT_TEXT.skipped);
    addImportLog(`  ⚠ Skipped — ${data.reason || IMPORT_TEXT.skipped}`, 'warning');
  } else {
    setText('import-current-status', data.reason || IMPORT_TEXT.failed);
    addImportLog(`  ✖ Failed — ${data.reason || IMPORT_TEXT.failed}`, 'error');
  }
}

function handleImportDone(data) {
  importState.finalResult = data;
  addImportLog('Import finished.', 'info');
}

function handleImportError(data) {
  const message = data.message || IMPORT_TEXT.importFailed;

  importState.streamError = message;
  addImportLog(message, 'error');
}

function cancelImport() {
  if (!importState.controller) return;

  addImportLog('Cancelling import...', 'warning');

  importState.controller.abort();
}

function stopImport(silent = false) {
  if (!importState.controller) return;

  importState.silentAbort = silent;
  importState.controller.abort();
}

function showResult(result, options = {}) {
  const summary = result.summary || {};
  const results = result.results || [];
  const failed = summary.failed || 0;
  const tone = options.tone || (failed ? 'warning' : 'success');
  const icon = options.icon || (failed ? 'alert-triangle' : 'check');
  const title = options.title || (failed ? 'Import Finished' : 'Import Complete');

  document.getElementById('import-result-imported').textContent = summary.imported || 0;
  document.getElementById('import-result-skipped').textContent = summary.skipped || 0;
  document.getElementById('import-result-failed').textContent = summary.failed || 0;

  const avatar = document.getElementById('import-result-avatar');

  if (avatar) {
    ['bg-success-lt', 'bg-warning-lt', 'bg-danger-lt'].forEach(className => {
      avatar.classList.toggle(className, className === `bg-${tone}-lt`);
    });
  }

  const iconElement = document.getElementById('import-result-icon');

  if (iconElement) iconElement.className = `ti ti-${icon} fs-1`;

  const titleElement = document.getElementById('import-result-title');

  if (titleElement) titleElement.textContent = title;

  const message = document.getElementById('import-result-message');

  if (message) {
    message.textContent =
      options.message ||
      `${summary.imported || 0} imported, ${summary.skipped || 0} skipped, ${summary.failed || 0} failed.`;
  }

  const problems = results.filter(item => item.status !== 'imported');
  const problemsCard = document.getElementById('import-result-problems');
  const problemList = document.getElementById('import-result-problem-list');

  if (problemsCard && problemList) {
    problemsCard.classList.toggle('d-none', problems.length === 0);

    problemList.innerHTML = problems
      .map(
        item => `
          <div class="list-group-item">
            <div class="fw-bold text-truncate">${escapeHtml(item.filename)}</div>
            <div class="text-muted small">${escapeHtml(item.reason || item.status)}</div>
          </div>
        `
      )
      .join('');
  }

  setView('result');

  if ((summary.imported || 0) > 0) {
    document.dispatchEvent(new Event('library:novel-updated'));
  }
}

async function submit() {
  const filenames = [...state.selected];

  if (!filenames.length) return;

  resetImportProgress();
  resetImportLog();
  setView('progress');

  const controller = new AbortController();

  importState.controller = controller;
  importState.silentAbort = false;

  try {
    await streamImport(
      filenames,
      {
        start: handleImportStart,
        file_start: handleImportFileStart,
        stage: handleImportStage,
        file_done: handleImportFileDone,
        done: handleImportDone,
        error: handleImportError
      },
      controller.signal
    );

    if (importState.finalResult) {
      showResult(importState.finalResult);
    } else if (importState.streamError) {
      window.showLibraryNotification?.(importState.streamError, 'error');
      showResult(partialResult());
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      if (!importState.silentAbort) {
        addImportLog('Import cancelled.', 'warning');
        showResult(partialResult(), {
          title: 'Import Cancelled',
          icon: 'cancel',
          tone: 'warning',
          message: `Import cancelled after ${
            importState.imported + importState.skipped + importState.failed
          } of ${importState.total} files.`
        });
      }

      return;
    }

    const message = error.message || IMPORT_TEXT.importFailed;

    window.showLibraryNotification?.(message, 'error');
    addImportLog(message, 'error');
    showResult(partialResult(), {
      title: 'Import Failed',
      icon: 'alert-circle',
      tone: 'danger'
    });
  } finally {
    importState.controller = null;
    importState.silentAbort = false;
  }
}

export function initImportPanel() {
  const panel = document.getElementById('import-offcanvas');

  if (!panel) return;

  setDirectory();

  document.getElementById('import-scan')?.addEventListener('click', scan);
  document.getElementById('import-back')?.addEventListener('click', () => setView('config'));
  document.getElementById('import-submit')?.addEventListener('click', submit);
  document.getElementById('import-cancel')?.addEventListener('click', cancelImport);

  document.getElementById('import-log-clear')?.addEventListener('click', () => {
    const list = document.getElementById('import-log-list');

    if (list) list.innerHTML = '';
  });

  document.getElementById('import-select-all')?.addEventListener('change', event => {
    state.selected = event.target.checked
      ? new Set(selectableCandidates().map(candidate => candidate.filename))
      : new Set();

    updateSelectionUI();
  });

  document.getElementById('import-candidate-list')?.addEventListener('change', event => {
    const input = event.target.closest('.import-candidate-check');

    if (!input) return;

    if (input.checked) {
      state.selected.add(input.dataset.filename);
    } else {
      state.selected.delete(input.dataset.filename);
    }

    updateSelectionUI();
  });

  panel.addEventListener('shown.bs.offcanvas', () => setDirectory());
  panel.addEventListener('hidden.bs.offcanvas', () => {
    stopScan();
    stopImport(true);
    resetImportLog();
    setView('config');
  });

  document.addEventListener('library:import-row-settings-changed', () => {
    if (state.candidates.length) {
      renderCandidateList();
    }
  });
}
