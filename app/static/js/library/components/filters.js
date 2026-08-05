import { getValue, nextFilterId } from "./../utils.js";
import { updateLibrary } from "./../app.js";
import {
  OPERATORS,
  FILTER_FIELDS,
  FILTER_MAP,
  TYPE_OPERATORS,
} from "./../config.js";

export function applyFilters(library) {
  if (!library.filters.length) return;
  library.visible = library.visible.filter((novel) => {
    switch (library.matchMode) {
      case "all":
        return library.filters.every((filter) => matchesFilter(novel, filter));
      case "any":
        return library.filters.some((filter) => matchesFilter(novel, filter));
      default:
        return true;
    }
  });
}

export function getFieldDefinition(field) {
  return FILTER_MAP.get(field);
}

export function getOperators(field) {
  return TYPE_OPERATORS[getFieldDefinition(field).type];
}

function matchesFilter(novel, filter) {
  const definition = getFieldDefinition(filter.field);
  if (!definition) return true;
  const value = definition.getter(novel);
  const operator = OPERATORS[filter.operator];
  const result = operator ? operator(value, filter.value) : true;

  return result;
}

export function initFilterPanel(library) {
  updateFilterPanel(library);

  document.getElementById("filter-reset").onclick = () => {
    library.filters = [];
    library.filterExpanded = null;

    updateFilterPanel(library);

    updateLibrary();
  };

  document.getElementById("filter-apply").onclick = () => {
    updateLibrary();
  };
}

export function updateFilterPanel(library) {
  const html = renderFilterContent(library);

  const content = document.getElementById("library-filter-content");

  content.innerHTML = html;

  bindFilterPanel(library);

  updateFilterButtons(library);
}

export function renderFilterContent(library) {
  return `
  <!-- Match Mode -->
  <div class="mb-4">
    <label class="form-label">Match</label>
    <div class="btn-group w-100">
    <input class="btn-check" type="radio" name="match-mode" id="match-all" value="all" ${library.matchMode === "all" ? "checked" : ""}>
    <label class="btn btn-outline-primary" for="match-all">All</label>
    <input class="btn-check" type="radio" name="match-mode" id="match-any" value="any" ${library.matchMode === "any" ? "checked" : ""}>
    <label class="btn btn-outline-primary" for="match-any">Any</label>
    </div>
  </div>
  <!-- Conditions -->
  <div class="mb-3">
    <label class="form-label">Conditions (${library.filters.length})</label>
    <div id="filter-list">${library.filters.length ? library.filters.map((filter, index) => renderFilterRow(filter, library)).join("") : renderEmptyState()}</div>
  </div>
  <button id="filter-add" class="btn btn-outline-primary w-100"> <i class="ti ti-plus me-1"></i>Add Condition</button>

  `;
}

function renderFilterRow(filter, library) {
  const field = FILTER_MAP.get(filter.field);
  const expanded = library.filterExpanded === filter.id;

  return `

<div class="card mb-3">
  <div class="card-header d-flex justify-content-between align-items-center library-filter-header" data-id="${filter.id}" style="cursor:pointer;">
    <div>
      <i class="ti ti-${field.icon} me-2"></i><strong>${field.label}</strong><span class="text-secondary mx-2">${filter.operator}</span><span class="badge bg-azure-lt filter-summary-value">${filter.value || "—"}</span>
    </div>
    <div class="d-flex align-items-center gap-2">
      <button class="btn btn-outline-danger btn-sm filter-delete" data-id="${filter.id}"><i class="ti ti-trash me-1"></i></button>
      <i class="ti ti-chevron-${expanded ? "up" : "down"}"></i>
    </div>
  </div>
  <div class="${expanded ? "" : "d-none"}">
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label">Field</label>
        <select class="form-select filter-field" data-id="${filter.id}">${renderFieldOptions(filter.field)}</select>
      </div>
      <div class="mb-3">
        <label class="form-label">Operator</label>
        <select class="form-select filter-operator" data-id="${filter.id}">${renderOperatorOptions(filter.field, filter.operator)}</select>
      </div>
      <div class="mb-3">
        <label class="form-label">Value</label>${renderValueControl(filter)}</div>
    </div>
  </div>
</div>
`;
}

function renderEmptyState() {
  return `
    <div class="empty">
      <div class="empty-img"><i class="ti ti-filter-off" style="font-size:48px;"></i></div>
      <p class="empty-title">No filters</p>
      <p class="empty-subtitle text-secondary">Click "Add Condition" to start filtering your library.</p>
    </div>
  `;
}

export function bindFilterPanel(library) {
  // Expand / Collapse
  document.querySelectorAll(".library-filter-header").forEach((header) => {
    header.onclick = () => {
      const id = Number(header.dataset.id);
      library.filterExpanded = library.filterExpanded === id ? null : id;
      updateFilterPanel(library);
    };
  });

  document.querySelectorAll("[name='match-mode']").forEach((radio) => {
    radio.onchange = () => {
      library.matchMode = radio.value;
      updateLibrary();
    };
  });

  // Add Condition
  document.getElementById("filter-add").onclick = () => {
    const definition = FILTER_FIELDS[0].items[0];

    const filter = {
      id: nextFilterId(),
      field: definition.field,
      operator: getOperators(definition.field)[0],
      value: "",
    };

    library.filters.push(filter);
    library.filterExpanded = filter.id;
    updateFilterPanel(library);
  };

  // Delete Condition
  document.querySelectorAll(".filter-delete").forEach((button) => {
    button.onclick = (e) => {
      e.stopPropagation();
      const id = Number(button.dataset.id);
      library.filters = library.filters.filter((f) => f.id !== id);
      if (library.filterExpanded === id)
        library.filterExpanded = library.filters.length
          ? library.filters[0].id
          : null;
      updateFilterPanel(library);
    };
  });

  // Field Condition
  document.querySelectorAll(".filter-field").forEach((select) => {
    select.onchange = () => {
      const filter = getFilter(library, Number(select.dataset.id));
      const definition = getFieldDefinition(select.value);

      filter.field = definition.field;
      filter.operator = getOperators(definition.field)[0];
      filter.value = "";

      updateFilterPanel(library);
    };
  });

  // Operator Condition
  document.querySelectorAll(".filter-operator").forEach((select) => {
    select.onchange = () => {
      const filter = getFilter(library, Number(select.dataset.id));
      filter.operator = select.value;
      const summary = select.closest(".card");
      summary.querySelector(".text-secondary").textContent = filter.operator;
      updateFilterButtons(library);
    };
  });

  // Value Condition
  document.querySelectorAll(".filter-value").forEach((control) => {
    const handler = () => {
      const filter = getFilter(library, Number(control.dataset.id));
      filter.value = control.value;
      updateFilterButtons(library);
      const card = control.closest(".card");
      card.querySelector(".filter-summary-value").textContent =
        filter.value || "—";
    };
    control.oninput = handler;
    control.onchange = handler;
  });
}

function updateFilterButtons(library) {
  const apply = document.getElementById("filter-apply");
  const reset = document.getElementById("filter-reset");

  if (!apply || !reset) return;

  apply.disabled = library.filters.length === 0;
  reset.disabled = library.filters.length === 0;
}

function renderFieldOptions(selected) {
  return FILTER_FIELDS.map(
    (group) => `
  <optgroup label="${group.category}">
    ${group.items
      .map(
        (field) => `
    <option value="${field.field}" ${field.field === selected ? "selected" : ""}>${field.label}</option>
    `,
      )
      .join("")}
  </optgroup>
  `,
  ).join("");
}

function renderOperatorOptions(field, selected) {
  return getOperators(field)
    .map(
      (operator) =>
        `<option value="${operator}" ${operator === selected ? "selected" : ""}> ${operator}</option>`,
    )
    .join("");
}

function renderValueControl(filter) {
  const field = getFieldDefinition(filter.field);
  switch (field.editor) {
    case "number":
      return `<input type="number" class="form-control filter-value" data-id="${filter.id}" value="${filter.value}">`;
    case "text":
      return `<input type="text" class="form-control filter-value" data-id="${filter.id}" value="${filter.value}">`;
    case "date":
      return `<input type="date" class="form-control filter-value" data-id="${filter.id}" value="${filter.value}">`;
    case "select":
      return `<select class="form-select filter-value" data-id="${filter.id}">${field.values.map((value) => `<option value="${value}" ${value === filter.value ? "selected" : ""}>${value}</option> `).join("")}</select>`;
    default:
      return `<input class="form-control filter-value" data-id="${filter.id}" value="${filter.value}">`;
  }
}

export function getFilter(library, id) {
  return library.filters.find((filter) => filter.id == id);
}

export function getFilterIndex(library, id) {
  return library.filters.findIndex((filter) => filter.id == id);
}
