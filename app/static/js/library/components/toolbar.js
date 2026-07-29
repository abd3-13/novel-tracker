import { SORT_OPTIONS } from "./sort.js";

function renderSortMenu(sort) {
    return SORT_OPTIONS.map(group => `
        <div class="dropdown-header">${group.group}</div>
        ${group.items.map(item => `
            <a href="#" class="dropdown-item library-sort-item ${item.field === sort.field ? "active" : ""}" data-field="${item.field}">
              <i class="ti ti-${item.icon} me-2"></i>${item.label}${item.field === sort.field ? `<span class="float-end sort-check"> <i class="ti ti-check"></i> </span>` : ""}
            </a>
            
        `).join("")}
    `).join('<div class="dropdown-divider"></div>');
}

export function updateSortButton(sort) {
    const arrow = sort.direction === "asc" ? "ti-sort-ascending" : "ti-sort-descending";
    const button = document.getElementById("library-sort-button");
    button.innerHTML = `<i class="ti ti-${sort.icon} me-1"></i>Sort : ${sort.label} <i class="ti ${arrow} ms-1"></i>`;
    
    // Remove previous active item
    document.querySelectorAll(".library-sort-item").forEach(item => {
        item.classList.remove("active");

        const check = item.querySelector(".sort-check");
        if (check) check.remove();
    });

    // Activate selected item
    const active = document.querySelector(`.library-sort-item[data-field="${sort.field}"]`
    );

    if (active) {
        active.classList.add("active");
        active.insertAdjacentHTML("beforeend", `<span class="float-end sort-check"><i class="ti ti-check"></i></span>`);
    }
}


export function bindToolbar(onSearch, onSort) {
    const search = document.getElementById("library-search");
    search.addEventListener("keydown", e => {
        if (e.key !== "Enter")
            return;
        onSearch(search.value.trim());
    });
    const options = SORT_OPTIONS.flatMap(g => g.items);
    document.querySelectorAll(".library-sort-item").forEach(item => {
        item.addEventListener("click", e => {
            e.preventDefault();
            const option = options.find(o => o.field === item.dataset.field);
            onSort(option);
        });
    });
}

export function renderToolbar(library) {
    document.getElementById("library-toolbar").innerHTML = `
      <div class="row g-2 align-items-center">
        <div class="col">
          <div class="input-icon">
            <span class="input-icon-addon"><i class="ti ti-search"></i></span>
            <input id="library-search" type="text" class="form-control" placeholder="Search novels...(title, description, tags, author, notes)" value="${library.search}">
          </div>
        </div>
        <div class="dropdown col-auto">
          <button id="library-sort-button" class="btn btn-outline-secondary" data-bs-toggle="dropdown"><i class="ti ti-${library.sort.icon} me-1"></i><span>Sort: ${library.sort.label}</span></button>
          <div class="dropdown-menu" id="sort-dropdown-menu">${renderSortMenu(library.sort)}</div>
        </div>
        <div class="col-auto"><button class="btn btn-outline-secondary" data-bs-toggle="offcanvas" data-bs-target="#library-filter-panel"><i class="ti ti-filter me-1"></i>Filter</button></div>
        <div class="col-auto"><button class="btn btn-outline-secondary">Bulk</button></div>
      </div>
    `;
}
