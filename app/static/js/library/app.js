import { fetchNovels } from "./api.js";
import { library } from "./state.js";
import { applySearch } from "./utils.js";
import { renderGrid } from "./views/grid.js";
import { renderHeader } from "./components/header.js";
import {
  applyFilters,
  initFilterPanel,
  bindFilterPanel,
  updateFilterPanel,
} from "./components/filters.js";
import {
  renderToolbar,
  bindToolbar,
  updateSortButton,
} from "./components/toolbar.js";
import { applySort } from "./components/sort.js";
import { renderNovelCard } from "./components/novel-card.js";
import { initSyncPanel } from "./components/sync.js";

async function init() {
  library.novels = await fetchNovels();

  renderLibrary(); // Build the UI once

  //updateLibrary();      // Populate the grid
}

function calculateStats() {
  library.stats.total = library.novels.length;

  library.stats.updates = library.novels.filter(
    (n) => n.chapters.diff > 0,
  ).length;

  library.stats.unread = library.novels.filter(
    (n) => n.reading.unread > 0,
  ).length;

  library.stats.missingEpub = library.novels.filter(
    (n) => !n.epub.exists,
  ).length;
}

export function renderLibrary() {
  renderHeader(library);

  renderToolbar(library);

  initFilterPanel(library);

  initSyncPanel();

  bindToolbar(
    (search) => {
      library.search = search;
      updateLibrary();
    },

    (option) => {
      if (library.sort.field === option.field) {
        option.direction = option.direction === "asc" ? "desc" : "asc";
      }

      library.sort = structuredClone(option);
      updateSortButton(library.sort);
      updateLibrary();
    },
  );

  //bindFilterPanel(library);
  updateLibrary();
}

export function updateLibrary() {
  library.visible = [...library.novels];

  applySearch(library);

  applySort(library);

  applyFilters(library);

  calculateStats();

  renderHeader(library);

  renderGrid(document.getElementById("library-content"), library.visible);
}

init();
