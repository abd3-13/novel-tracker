import { escapeHtml } from './../utils.js';
import { importEpubs, listenImportScan } from './../api.js';
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

function showResult(result) {
  const summary = result.summary || {};
  const results = result.results || [];

  document.getElementById('import-result-imported').textContent = summary.imported || 0;
  document.getElementById('import-result-skipped').textContent = summary.skipped || 0;
  document.getElementById('import-result-failed').textContent = summary.failed || 0;

  const message = document.getElementById('import-result-message');

  if (message) {
    message.textContent = `${summary.imported || 0} imported, ${summary.skipped || 0} skipped, ${summary.failed || 0} failed.`;
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

  const progress = document.getElementById('import-progress-count');

  if (progress) {
    progress.textContent = `${filenames.length} selected`;
  }

  setView('progress');

  try {
    const result = await importEpubs(filenames);
    showResult(result);
  } catch (error) {
    window.showLibraryNotification?.(error.message || IMPORT_TEXT.importFailed, 'error');
    setView('results');
  }
}

export function initImportPanel() {
  const panel = document.getElementById('import-offcanvas');

  if (!panel) return;

  setDirectory();

  document.getElementById('import-scan')?.addEventListener('click', scan);
  document.getElementById('import-back')?.addEventListener('click', () => setView('config'));
  document.getElementById('import-submit')?.addEventListener('click', submit);

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
    setView('config');
  });

  document.addEventListener('library:import-row-settings-changed', () => {
    if (state.candidates.length) {
      renderCandidateList();
    }
  });
}
