// static/js/library/views/grid.js

import { renderNovelCard, bindNovelCardActions } from '../components/novel-card.js';
import { getSelectedOverlayMetadata } from '../components/settings.js';

// Cards are rendered in batches across animation frames so a library with
// thousands of novels paints the first screen immediately instead of
// blocking the main thread while every card is parsed and inserted.
const BATCH_SIZE = 48;

let renderToken = 0;

export function renderGrid(container, novels) {
  const token = ++renderToken;

  container.innerHTML = `<div class="row row-cols-2 row-cols-md-4 row-cols-xl-6 g-3"></div>`;

  const grid = container.firstElementChild;

  bindNovelCardActions(grid, novels);

  // Resolve the overlay metadata once per render instead of once per card.
  const overlayMetadata = new Set(getSelectedOverlayMetadata());

  let index = 0;

  const renderBatch = () => {
    // A newer render started (search/sort/filter) or the grid was replaced.
    if (token !== renderToken || !grid.isConnected) return;

    const end = Math.min(index + BATCH_SIZE, novels.length);

    if (index < end) {
      let html = '';
      for (; index < end; index += 1) {
        html += renderNovelCard(novels[index], overlayMetadata);
      }
      // One parse + one reflow per batch instead of one per card.
      grid.insertAdjacentHTML('beforeend', html);
    }

    if (index < novels.length) {
      requestAnimationFrame(renderBatch);
    }
  };

  renderBatch();
}
