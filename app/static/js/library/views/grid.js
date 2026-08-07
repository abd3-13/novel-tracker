// static/js/library/views/grid.js

import { renderNovelCard } from '../components/novel-card.js';

export function renderGrid(container, novels) {
  container.innerHTML = `<div class="row row-cols-2 row-cols-md-4 row-cols-xl-6 g-3"></div>`;

  const grid = container.firstElementChild;

  novels.forEach(novel => {
    grid.insertAdjacentHTML('beforeend', renderNovelCard(novel));
  });
}

export function enableSelection(container) {
  container.addEventListener('click', e => {
    const card = e.target.closest('.novel-card');
    if (!card) return;

    card.classList.toggle('selected');
  });
}

export function getSelectedNovelIds(container) {
  return [...container.querySelectorAll('.novel-card.selected')].map(card => Number(card.dataset.id));
}
