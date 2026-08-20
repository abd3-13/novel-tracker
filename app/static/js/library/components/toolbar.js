import { SORT_OPTIONS } from './sort.js';
import { updateSelectionBar, exitSelectionMode, clearSelection, selectAll, selectBetweenSelected } from './selection.js';
import { library } from './../state.js';

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
  button.innerHTML = `<i class="ti ti-${sort.icon} me-1"></i><span class="d-none d-md-inline">Sort : ${sort.label}</span> <i class="ti ${arrow} ms-1"></i>`;

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

  document.getElementById('toolbar-select').addEventListener('click', () => {
    library.selectionMode = true;
    updateSelectionBar(library);
  });

  const container = document.getElementById('library-content');
  document.getElementById('selection-done').addEventListener('click', () => {
    exitSelectionMode(container, library);
  });

  document.getElementById('selection-clear').addEventListener('click', () => {
    clearSelection(container, library);
  });

  document.getElementById('selection-between').addEventListener('click', () => {
    selectBetweenSelected(container, library);
  });

  document.getElementById('selection-select-all').addEventListener('click', () => {
    selectAll(container, library);
  });
}

export function renderToolbar(library) {
  document.getElementById('library-toolbar').innerHTML = `
      <div class="row g-2 align-items-center">
        <div class="col">
          <div class="input-icon">
            <span class="input-icon-addon"><i class="ti ti-search"></i></span>
            <input id="library-search" type="text" class="form-control" placeholder="Search novels...(title, description, tags, author, notes)" value="${library.search}">
          </div>
        </div>
        <div class="dropdown col-auto">
          <button id="library-sort-button" class="btn btn-outline-secondary" data-bs-toggle="dropdown"><i class="ti ti-${library.sort.icon} me-1"></i><span class="d-none d-md-inline">Sort: ${library.sort.label}</span></button>
          <div class="dropdown-menu" id="sort-dropdown-menu">${renderSortMenu(library.sort)}</div>
        </div>
        <div class="col-auto"><button id="toolbar-filter" class="btn btn-outline-secondary" data-bs-toggle="offcanvas" data-bs-target="#library-filter-panel"><i class="ti ti-filter me-1"></i><span class="d-none d-md-inline">Filter</span></button></div>
        <div class="col-auto"><button id="toolbar-sync" class="btn btn-outline-secondary" data-bs-toggle="offcanvas" data-bs-target="#sync-offcanvas"><i class="ti ti-refresh me-1"></i><span class="d-none d-md-inline">Synchronize</span></button></div>
         <div class="col-auto"><button id="toolbar-select" class="btn btn-outline-secondary"><i class="ti ti-checkbox me-1"></i><span class="d-none d-md-inline">Select</span></button></div>
        </div>
      <div id="library-selection-bar" class="mt-2 d-none">
            <div class="card">
                <div class="card-body py-2">
                    <div class="d-flex align-items-center gap-2">
                        <div class="flex-fill"><i class="ti ti-checkbox me-1"></i><strong id="selection-count">0 selected</strong></div>
                        <button id="selection-between" class="btn btn-sm btn-outline-secondary"><i class="ti ti-arrows-horizontal me-1"></i>Between</button>
                        <button id="selection-select-all" class="btn btn-sm btn-outline-secondary"><i class="ti ti-select-all me-1"></i>Select all</button>
                        <button id="selection-clear" class="btn btn-sm btn-outline-secondary"><i class="ti ti-x me-1"></i>Clear</button>
                        <button id="selection-done" class="btn btn-sm btn-primary"><i class="ti ti-check me-1"></i>Done</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}
