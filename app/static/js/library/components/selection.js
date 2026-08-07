import { library } from './../state.js';

export function enableSelection(container, library) {
  container.addEventListener('click', e => {
    if (!library.selectionMode) return;

    const card = e.target.closest('.novel-card');
    if (!card) return;

    if (e.target.closest('button, a, input')) return;

    const id = Number(card.dataset.id);
    const selected = card.classList.toggle('selected');

    if (selected) {
      library.ids.add(id);
    } else {
      library.ids.delete(id);
    }
    updateSelectionBar(library);

    library.onSelectionChange?.();
  });
}

export function getSelectedNovelIds(container) {
  return [...container.querySelectorAll('.novel-card.selected')].map(card => Number(card.dataset.id));
}

export function clearSelection(container, library) {
  container.querySelectorAll('.novel-card.selected').forEach(card => card.classList.remove('selected'));

  library.ids.clear();
  library.onSelectionChange?.();
}

export function selectAll(container, library) {
  container.querySelectorAll('.novel-card').forEach(card => {
    const id = Number(card.dataset.id);

    card.classList.add('selected');
    library.ids.add(id);
  });

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

  updateSelectionBar(library);
}
