import { SORT_OPTIONS } from './sort.js';
import {
  updateSelectionBar,
  exitSelectionMode,
  clearSelection,
  selectAll,
  selectBetweenSelected
} from './selection.js';
import { library, getLibrarySyncIds } from './../state.js';
import { TOOLBAR_TEXT, SELECTION_TEXT } from './../config.js';
import { IS_ADMIN } from './../permissions.js';

function renderSortMenu(sort) {
  return SORT_OPTIONS.map(
    group => `
        <div class="dropdown-header">${group.group}</div>
        ${group.items
          .map(
            item => `
            <a href="#" class="dropdown-item library-sort-item ${item.field === sort.field ? 'active' : ''}" data-field="${item.field}">
              <i class="ti ti-${item.icon} me-2"></i>${item.label}${item.field === sort.field ? `<span class="float-end sort-check"> <i class="ti ti-check"></i> </span>` : ''}
            </a>

        `
          )
          .join('')}
    `
  ).join('<div class="dropdown-divider"></div>');
}

export function updateSortButton(sort) {
  const arrow = sort.direction === 'asc' ? 'ti-sort-ascending' : 'ti-sort-descending';
  const button = document.getElementById('library-sort-button');
  button.innerHTML = `<i class="ti ti-${sort.icon} me-1"></i><span class="d-none d-md-inline">${TOOLBAR_TEXT.sort}: ${sort.label}</span> <i class="ti ${arrow} ms-1"></i>`;

  // Remove previous active item
  document.querySelectorAll('.library-sort-item').forEach(item => {
    item.classList.remove('active');

    const check = item.querySelector('.sort-check');
    if (check) check.remove();
  });

  // Activate selected item
  const active = document.querySelector(`.library-sort-item[data-field="${sort.field}"]`);

  if (active) {
    active.classList.add('active');
    active.insertAdjacentHTML('beforeend', `<span class="float-end sort-check"><i class="ti ti-check"></i></span>`);
  }
}

export function bindToolbar(onSearch, onSort) {
  const search = document.getElementById('library-search');
  search.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    onSearch(search.value.trim());
  });
  const options = SORT_OPTIONS.flatMap(g => g.items);
  document.querySelectorAll('.library-sort-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      const option = options.find(o => o.field === item.dataset.field);
      onSort(option);
    });
  });

  library.onSelectionChange = updateSyncActionCount;

  document.getElementById('toolbar-select')?.addEventListener('click', () => {
    library.selectionMode = true;
    updateSelectionBar(library);
    updateSyncActionCount();
  });

  const container = document.getElementById('library-content');
  document.getElementById('selection-done').addEventListener('click', () => {
    exitSelectionMode(container, library);
    updateSyncActionCount();
  });

  document.getElementById('selection-clear').addEventListener('click', () => {
    clearSelection(container, library);
    updateSyncActionCount();
  });

  document.getElementById('selection-between').addEventListener('click', () => {
    selectBetweenSelected(container, library);
    updateSyncActionCount();
  });

  document.getElementById('selection-select-all').addEventListener('click', () => {
    selectAll(container, library);
    updateSyncActionCount();
  });
}

export function updateSyncActionCount() {
  const button = document.getElementById('toolbar-sync');
  const count = document.getElementById('toolbar-sync-count');

  if (!button || !count) return;

  const total = getLibrarySyncIds().length;

  count.textContent = ` (${total})`;
  button.disabled = total === 0;
  button.classList.toggle('disabled', total === 0);
}

export function renderToolbar(library) {
  const filterCount = library.filters.length;
  const syncCount = getLibrarySyncIds().length;

  document.getElementById('library-toolbar').innerHTML = `
      <div class="row g-2 align-items-center">
        <div class="col">
          <div class="input-icon">
            <span class="input-icon-addon"><i class="ti ti-search"></i></span>
            <input id="library-search" type="text" class="form-control" placeholder="${TOOLBAR_TEXT.searchPlaceholder}" value="${library.search}">
          </div>
        </div>
        <div class="col-auto">
          <button id="toolbar-filter" class="btn btn-outline-secondary" data-bs-toggle="offcanvas" data-bs-target="#library-filter-panel">
            <i class="ti ti-filter me-1"></i><span class="d-none d-md-inline">${TOOLBAR_TEXT.filter}</span>
            <span id="toolbar-filter-count" class="badge bg-primary ms-1 ${filterCount ? '' : 'd-none'}">${filterCount}</span>
          </button>
        </div>
        <div class="dropdown col-auto">
          <button id="library-sort-button" class="btn btn-outline-secondary" data-bs-toggle="dropdown"><i class="ti ti-${library.sort.icon} me-1"></i><span class="d-none d-md-inline">${TOOLBAR_TEXT.sort}: ${library.sort.label}</span></button>
          <div class="dropdown-menu" id="sort-dropdown-menu">${renderSortMenu(library.sort)}</div>
        </div>
        ${IS_ADMIN ? `<div class="col-auto">
          <div class="dropdown">
            <button id="toolbar-actions" class="btn btn-outline-secondary" data-bs-toggle="dropdown" aria-expanded="false" title="${TOOLBAR_TEXT.actions}"><i class="ti ti-dots-vertical"></i><span class="d-none d-md-inline ms-1">${TOOLBAR_TEXT.actions}</span></button>
            <div class="dropdown-menu dropdown-menu-end">
              <div class="dropdown-header">Library</div>
              <button type="button" id="toolbar-import" class="dropdown-item" data-bs-toggle="offcanvas" data-bs-target="#import-offcanvas"><i class="ti ti-file-import me-2"></i>${TOOLBAR_TEXT.import}</button>
              <button type="button" id="toolbar-sync" class="dropdown-item ${syncCount === 0 ? 'disabled' : ''}" data-bs-toggle="offcanvas" data-bs-target="#sync-offcanvas" ${syncCount === 0 ? 'disabled' : ''}><i class="ti ti-refresh me-2"></i>${TOOLBAR_TEXT.synchronize}<span id="toolbar-sync-count"> (${syncCount})</span></button>
              <div class="dropdown-divider"></div>
              <button type="button" id="toolbar-select" class="dropdown-item"><i class="ti ti-checkbox me-2"></i>${TOOLBAR_TEXT.select}</button>
            </div>
          </div>
        </div>` : ''}
      </div>
      <div id="library-selection-bar" class="mt-2 d-none">
            <div class="card">
                <div class="card-body py-2">
                    <div class="d-flex align-items-center gap-2">
                        <div class="flex-fill"><i class="ti ti-checkbox me-1"></i><strong id="selection-count">${SELECTION_TEXT.selected.replace('{count}', 0)}</strong></div>
                        <button id="selection-between" class="btn btn-sm btn-outline-secondary"><i class="ti ti-arrows-horizontal me-1"></i>${SELECTION_TEXT.between}</button>
                        <button id="selection-select-all" class="btn btn-sm btn-outline-secondary"><i class="ti ti-select-all me-1"></i>${SELECTION_TEXT.selectAll}</button>
                        <button id="selection-clear" class="btn btn-sm btn-outline-secondary"><i class="ti ti-x me-1"></i>${SELECTION_TEXT.clear}</button>
                        <button id="selection-done" class="btn btn-sm btn-primary"><i class="ti ti-check me-1"></i>${SELECTION_TEXT.done}</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}
