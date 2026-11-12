import { escapeHtml, getValue, nextFilterId } from './../utils.js';
import { updateLibrary } from './../app.js';
import { OPERATORS, FILTER_FIELDS, FILTER_MAP, TYPE_OPERATORS, FILTER_TEXT } from './../config.js';

export function applyFilters(library) {
  if (!library.filters.length) return;

  library.visible = library.visible.filter(novel => {
    switch (library.matchMode) {
      case 'all':
        return library.filters.every(filter => matchesFilter(novel, filter));
      case 'any':
        return library.filters.some(filter => matchesFilter(novel, filter));
      default:
        return true;
    }
  });
}

export function getFieldDefinition(field) {
  return FILTER_MAP.get(field);
}

export function getOperators(field) {
  const definition = getFieldDefinition(field);

  return definition ? TYPE_OPERATORS[definition.type] || [] : [];
}

function matchesFilter(novel, filter) {
  const definition = getFieldDefinition(filter.field);

  if (!definition) return true;

  const value = definition.getter(novel);
  const operator = OPERATORS[filter.operator];

  return operator ? operator(value, filter.value) : true;
}

export function initFilterPanel(library) {
  updateFilterPanel(library);

  document.getElementById('filter-reset').onclick = () => {
    library.filters = [];
    library.filterExpanded = null;

    updateFilterPanel(library);

    updateLibrary();
  };

  document.getElementById('filter-apply').onclick = () => {
    updateLibrary();
  };
}

export function updateFilterPanel(library) {
  const content = document.getElementById('library-filter-content');

  content.innerHTML = renderFilterContent(library);

  bindFilterPanel(library);

  updateFilterButtons(library);
}

export function renderFilterContent(library) {
  return `
  <!-- Match Mode -->
  <div class="mb-4">
    <label class="form-label">${escapeHtml(FILTER_TEXT.match)}</label>
    <div class="btn-group w-100">
    <input class="btn-check" type="radio" name="match-mode" id="match-all" value="all" ${library.matchMode === 'all' ? 'checked' : ''}>
    <label class="btn btn-outline-primary" for="match-all">${escapeHtml(FILTER_TEXT.all)}</label>
    <input class="btn-check" type="radio" name="match-mode" id="match-any" value="any" ${library.matchMode === 'any' ? 'checked' : ''}>
    <label class="btn btn-outline-primary" for="match-any">${escapeHtml(FILTER_TEXT.any)}</label>
    </div>
  </div>
  <!-- Conditions -->
  <div class="mb-3">
    <label class="form-label">${escapeHtml(FILTER_TEXT.conditions)} (${library.filters.length})</label>
    <div id="filter-list">${library.filters.length ? library.filters.map(filter => renderFilterRow(filter, library)).join('') : renderEmptyState()}</div>
  </div>
  <button id="filter-add" class="btn btn-outline-primary w-100"> <i class="ti ti-plus me-1"></i>${escapeHtml(FILTER_TEXT.addCondition)}</button>

  `;
}

function renderFilterRow(filter, library) {
  const field = getFieldDefinition(filter.field);

  // A filter can end up pointing at a field that no longer exists in
  // FILTER_FIELDS (e.g. config changed under a persisted filter set).
  // Render nothing for that row rather than throwing on field.icon/label.
  if (!field) return '';

  const expanded = library.filterExpanded === filter.id;
  const summaryValue = filter.value ? escapeHtml(filter.value) : FILTER_TEXT.emptyValue;

  return `

<div class="card mb-3">
  <div class="card-header d-flex justify-content-between align-items-center library-filter-header" data-id="${filter.id}" style="cursor:pointer;">
    <div>
      <i class="ti ti-${field.icon} me-2"></i><strong>${escapeHtml(field.label)}</strong><span class="text-secondary mx-2 filter-summary-operator">${escapeHtml(filter.operator)}</span><span class="badge bg-azure-lt filter-summary-value">${summaryValue}</span>
    </div>
    <div class="d-flex align-items-center gap-2">
      <button class="btn btn-outline-danger btn-sm filter-delete" data-id="${filter.id}"><i class="ti ti-trash me-1"></i></button>
      <i class="ti ti-chevron-${expanded ? 'up' : 'down'}"></i>
    </div>
  </div>
  <div class="${expanded ? '' : 'd-none'}">
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label">${escapeHtml(FILTER_TEXT.field)}</label>
        <select class="form-select filter-field" data-id="${filter.id}">${renderFieldOptions(filter.field)}</select>
      </div>
      <div class="mb-3">
        <label class="form-label">${escapeHtml(FILTER_TEXT.operator)}</label>
        <select class="form-select filter-operator" data-id="${filter.id}">${renderOperatorOptions(filter.field, filter.operator)}</select>
      </div>
      <div class="mb-3">
        <label class="form-label">${escapeHtml(FILTER_TEXT.value)}</label>${renderValueControl(filter)}</div>
    </div>
  </div>
</div>
`;
}

function renderEmptyState() {
  return `
    <div class="empty">
      <div class="empty-img"><i class="ti ti-filter-off" style="font-size:48px;"></i></div>
      <p class="empty-title">${escapeHtml(FILTER_TEXT.noFilters)}</p>
      <p class="empty-subtitle text-secondary">${escapeHtml(FILTER_TEXT.noFiltersHint)}</p>
    </div>
  `;
}

export function bindFilterPanel(library) {
  // Expand / Collapse
  document.querySelectorAll('.library-filter-header').forEach(header => {
    header.onclick = () => {
      const id = Number(header.dataset.id);
      library.filterExpanded = library.filterExpanded === id ? null : id;
      updateFilterPanel(library);
    };
  });

  document.querySelectorAll("[name='match-mode']").forEach(radio => {
    radio.onchange = () => {
      library.matchMode = radio.value;
      updateLibrary();
    };
  });

  // Add Condition
  document.getElementById('filter-add').onclick = () => {
    const definition = FILTER_FIELDS[0].items[0];

    const filter = {
      id: nextFilterId(),
      field: definition.field,
      operator: getOperators(definition.field)[0],
      value: definition.values?.[0] ?? ''
    };

    library.filters.push(filter);
    library.filterExpanded = filter.id;
    updateFilterPanel(library);
  };

  // Delete Condition
  document.querySelectorAll('.filter-delete').forEach(button => {
    button.onclick = e => {
      e.stopPropagation();
      const id = Number(button.dataset.id);
      library.filters = library.filters.filter(f => f.id !== id);
      if (library.filterExpanded === id) library.filterExpanded = library.filters.length ? library.filters[0].id : null;
      updateFilterPanel(library);
    };
  });

  // Field Condition
  document.querySelectorAll('.filter-field').forEach(select => {
    select.onchange = () => {
      const filter = getFilter(library, select.dataset.id);
      const definition = getFieldDefinition(select.value);

      filter.field = definition.field;
      filter.operator = getOperators(definition.field)[0];
      filter.value = definition.values?.[0] ?? '';

      updateFilterPanel(library);
    };
  });

  // Operator Condition
  document.querySelectorAll('.filter-operator').forEach(select => {
    select.onchange = () => {
      const filter = getFilter(library, select.dataset.id);
      filter.operator = select.value;

      const summary = select.closest('.card');
      summary.querySelector('.filter-summary-operator').textContent = filter.operator;

      updateFilterButtons(library);
    };
  });

  // Value Condition
  document.querySelectorAll('.filter-value').forEach(control => {
    const handler = () => {
      const filter = getFilter(library, control.dataset.id);
      filter.value = control.value;

      updateFilterButtons(library);

      const card = control.closest('.card');
      card.querySelector('.filter-summary-value').textContent = filter.value || FILTER_TEXT.emptyValue;
    };

    control.oninput = handler;
    control.onchange = handler;
  });
}

function updateFilterButtons(library) {
  const count = document.getElementById('toolbar-filter-count');

  if (count) {
    count.textContent = library.filters.length;
    count.classList.toggle('d-none', library.filters.length === 0);
  }

  const apply = document.getElementById('filter-apply');
  const reset = document.getElementById('filter-reset');

  if (!apply || !reset) return;

  apply.disabled = library.filters.length === 0;
  reset.disabled = library.filters.length === 0;
}

function renderFieldOptions(selected) {
  return FILTER_FIELDS.map(
    group => `
  <optgroup label="${escapeHtml(group.category)}">
    ${group.items
      .map(
        field => `
    <option value="${field.field}" ${field.field === selected ? 'selected' : ''}>${escapeHtml(field.label)}</option>
    `
      )
      .join('')}
  </optgroup>
  `
  ).join('');
}

function renderOperatorOptions(field, selected) {
  return getOperators(field)
    .map(operator => `<option value="${operator}" ${operator === selected ? 'selected' : ''}> ${escapeHtml(operator)}</option>`)
    .join('');
}

// number/text/date editors only ever differ by the `type` attribute — the
// old code repeated the same markup three times plus a fourth "no type"
// default that's functionally identical to type="text".
const SIMPLE_VALUE_EDITORS = new Set(['number', 'text', 'date']);

function renderValueControl(filter) {
  const field = getFieldDefinition(filter.field);

  if (field?.editor === 'select') {
    return renderSelectValueControl(filter, field);
  }

  const inputType = SIMPLE_VALUE_EDITORS.has(field?.editor) ? field.editor : 'text';

  return renderPlainValueInput(filter, inputType);
}

function renderPlainValueInput(filter, type = 'text') {
  return `<input type="${type}" class="form-control filter-value" data-id="${filter.id}" value="${escapeHtml(String(filter.value ?? ''))}">`;
}

function renderSelectValueControl(filter, field) {
  const options = field.values
    .map(value => `<option value="${escapeHtml(String(value))}" ${value === filter.value ? 'selected' : ''}>${escapeHtml(String(value))}</option> `)
    .join('');

  return `<select class="form-select filter-value" data-id="${filter.id}">${options}</select>`;
}

export function getFilter(library, id) {
  const numId = Number(id);

  return library.filters.find(filter => filter.id === numId);
}

export function getFilterIndex(library, id) {
  const numId = Number(id);

  return library.filters.findIndex(filter => filter.id === numId);
}
