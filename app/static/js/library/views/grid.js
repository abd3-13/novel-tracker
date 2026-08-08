// static/js/library/views/grid.js

import { renderNovelCard, initNovelTitleScrolling } from '../components/novel-card.js';
import { library } from './../state.js';

export function renderGrid(container, novels) {
  container.innerHTML = `<div class="row row-cols-2 row-cols-md-4 row-cols-xl-6 g-3"></div>`;

  const grid = container.firstElementChild;

  novels.forEach(novel => {
    grid.insertAdjacentHTML('beforeend', renderNovelCard(novel));
  });

  initNovelTitleScrolling();
}
