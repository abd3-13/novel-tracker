// static/js/library/components/novel-card.js

import { STATUS_STYLE } from './../config.js';
import { getSelectedOverlayMetadata } from './settings.js';
import { CARD_METADATA } from './card-metadata.js';

function renderMeta(icon, value, title = '') {
  if (value === null || value === undefined || value === '' || value === 0 || value === '0' || value === '0/0') return '';

  return `
        <div class="nt-meta-item" title="${title}"><i class="ti ti-${icon}"></i><span>${value}</span></div>`;
}

export function initNovelTitleScrolling() {
  const mobileQuery = window.matchMedia('(max-width: 767.98px)');

  if (!mobileQuery.matches) {
    return;
  }

  const titles = document.querySelectorAll('.nt-title-scroll');

  if (!titles.length) {
    return;
  }

  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        const title = entry.target;
        const container = title.parentElement;

        if (!entry.isIntersecting) {
          title.classList.remove('is-scrolling');
          return;
        }

        requestAnimationFrame(() => {
          const overflow = title.scrollWidth - container.clientWidth;

          // Title fits — nothing to scroll
          if (overflow <= 2) {
            title.classList.remove('is-scrolling');
            return;
          }

          title.style.setProperty('--nt-scroll-distance', `-${overflow}px`);

          // Longer titles get more time
          const duration = Math.min(10, Math.max(5, overflow / 15));

          title.style.setProperty('--nt-scroll-duration', `${duration}s`);

          title.classList.add('is-scrolling');
        });
      });
    },
    {
      threshold: 0.75
    }
  );

  titles.forEach(title => observer.observe(title));
}

export function renderNovelCard(novel) {
  const unread = novel.reading.unread;

  const status = STATUS_STYLE[novel.status] ?? STATUS_STYLE.Reading;

  const percent = novel.chapters.online > 0 ? Math.round((novel.chapters.local / novel.chapters.online) * 100) : 0;
  const cover = 'cover.webp';
  const selectedOverlayMetadata = new Set(getSelectedOverlayMetadata());

  const optionalMeta = CARD_METADATA.filter(metadata => metadata.overlay && selectedOverlayMetadata.has(metadata.id))
    .map(metadata => {
      const value = metadata.getValue(novel);
      const title = metadata.getTitle ? metadata.getTitle(novel) : metadata.label;

      return renderMeta(metadata.icon, value, title);
    })
    .join('');

  return `
  <div class="col">
    <div class="card novel-card bg-transparent border-0 shadow h-100" data-id="${novel.id}">
      <div class="position-relative novel-cover">
        <img src="static/img/cover/${cover}" class="novel-cover-img card-img-top rounded-1" onerror="this.onerror=null; this.src='static/img/cover/cover.webp';">
        <!--<div class="nt-cover-top-overlay rounded-top-1"></div>-->
        ${unread > 0 ? ` <span class="badge bg-red text-white position-absolute top-0 start-0 m-2">+${unread}</span> ` : ''}
        <!--<div class="badge bg-dark-lt position-absolute top-0 end-0 me-1">
          <a class="btn btn-icon btn-sm p-0 ms-1 border-0 bg-transparent" href="${novel.source.url}" role="button">🌐</a>
        </div>-->
        <div class="position-absolute top-50 end-0 translate-middle-y me-2 d-flex flex-column align-items-end gap-1">${optionalMeta}</div>
        <div class="position-absolute start-0 ms-2" style="bottom: 20px;"><span class="badge ${status.bg} ${status.text} fs-6">${novel.status}</span></div>
        <div class="position-absolute bottom-0 start-0 end-0">
          <div class="progress rounded-0 position-relative" style="height: 15px;">
              <div class="progress-bar fw-bold" style="width:${percent}%"></div>
              <span class="position-absolute top-50 start-50 translate-middle fw-bold">${novel.chapters.local}/${novel.chapters.online}</span>
          </div>
        </div>
      </div>
      <div class="card-body p-2">
        <div class="nt-title-container" data-bs-toggle="tooltip" data-bs-placement="bottom" title="${novel.title}"><div class="nt-title-scroll fw-bold">${novel.title}</div></div>
        <div class="text-secondary text-truncate text-end small">${novel.author}</div>
      </div>
    </div>
  </div>

    `;
}
