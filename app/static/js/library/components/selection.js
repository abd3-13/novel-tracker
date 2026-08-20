import { library } from './../state.js';

function getVisibleNovelOrder(container) {
  return [...container.querySelectorAll('.novel-card')].map(card => Number(card.dataset.id));
}

export function enableSelection(container, library) {
  container.addEventListener('click', e => {
    if (!library.selectionMode) return;

    const card = e.target.closest('.novel-card');
    if (!card) return;

    if (e.target.closest('button, a, input')) return;

    const id = Number(card.dataset.id);

    if (e.shiftKey && library.selectionAnchor !== null) {
      selectBetweenIds(container, library, library.selectionAnchor, id);
      return;
    }

    const selected = card.classList.toggle('selected');

    if (selected) {
      library.ids.add(id);
      library.selectionAnchor = id;
    } else {
      library.ids.delete(id);
      if (library.selectionAnchor === id) {
        library.selectionAnchor = null;
      }
    }
    updateSelectionBar(library);

    library.onSelectionChange?.();
  });
}

export function getSelectedNovelIds(container) {
  return [...container.querySelectorAll('.novel-card.selected')].map(card => Number(card.dataset.id));
}

export function selectBetweenIds(container, library, fromId, toId) {
  const visibleIds = getVisibleNovelOrder(container);

  if (!visibleIds.length || fromId === undefined || toId === undefined) {
    return;
  }

  const fromIndex = visibleIds.indexOf(fromId);
  const toIndex = visibleIds.indexOf(toId);

  if (fromIndex === -1 || toIndex === -1) {
    return;
  }

  const start = Math.min(fromIndex, toIndex);
  const end = Math.max(fromIndex, toIndex);
  const rangeIds = new Set(visibleIds.slice(start, end + 1));

  visibleIds.forEach(id => {
    const card = container.querySelector(`.novel-card[data-id="${id}"]`);
    if (!card) return;

    const isInRange = rangeIds.has(id);
    card.classList.toggle('selected', isInRange);

    if (isInRange) {
      library.ids.add(id);
    } else {
      library.ids.delete(id);
    }
  });

  library.selectionAnchor = toId;
  updateSelectionBar(library);
  library.onSelectionChange?.();
}

export function selectBetweenSelected(container, library) {
  const visibleIds = getVisibleNovelOrder(container);
  const selectedIds = visibleIds.filter(id => library.ids.has(id));

  if (selectedIds.length < 2) {
    return;
  }

  const fromId = selectedIds[0];
  const toId = selectedIds[selectedIds.length - 1];
  selectBetweenIds(container, library, fromId, toId);
}

export function clearSelection(container, library) {
  container.querySelectorAll('.novel-card.selected').forEach(card => card.classList.remove('selected'));

  library.ids.clear();
  library.selectionAnchor = null;
  updateSelectionBar(library);
  library.onSelectionChange?.();
}

export function selectAll(container, library) {
  container.querySelectorAll('.novel-card').forEach(card => {
    const id = Number(card.dataset.id);

    card.classList.add('selected');
    library.ids.add(id);
  });

  library.selectionAnchor = null;
  updateSelectionBar(library);
  library.onSelectionChange?.();
}

export function updateSelectionBar(library) {
  const bar = document.getElementById('library-selection-bar');
  const count = document.getElementById('selection-count');

  if (!bar || !count) return;

  count.textContent = `${library.ids.size} selected`;

  bar.classList.toggle('d-none', !library.selectionMode);
}

export function enterSelectionMode(library) {
  library.selectionMode = true;
  updateSelectionBar(library);
}

export function exitSelectionMode(container, library) {
  library.selectionMode = false;

  container.querySelectorAll('.novel-card.selected').forEach(card => {
    card.classList.remove('selected');
  });

  library.ids.clear();
  library.selectionAnchor = null;

  updateSelectionBar(library);
}
