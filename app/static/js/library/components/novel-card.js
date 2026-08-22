// static/js/library/components/novel-card.js

import { timeAgo } from './../utils.js';
import { STATUS_STYLE } from './../config.js';
import { getSelectedOverlayMetadata } from './settings.js';

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

  const metaConfig = [
    {
      id: 'characters',
      enabled: selectedOverlayMetadata.has('characters'),
      icon: 'users',
      value: `${novel.characters.local}/${novel.characters.online}`,
      title: `Characters: Local - ${novel.characters.local} | Online - ${novel.characters.online}`
    },
    { id: 'progress', enabled: selectedOverlayMetadata.has('progress'), icon: 'percentage', value: `${novel.reading.percent}%`, title: 'Read progress %' },
    {
      id: 'chapter',
      enabled: selectedOverlayMetadata.has('chapter'),
      icon: 'bookmark',
      value: novel.reading.chapter,
      title: `Currently on Ch${novel.reading.chapter}`
    },
    { id: 'updates', enabled: selectedOverlayMetadata.has('updates'), icon: 'bookmarks', value: novel.chapters.diff, title: 'New chapters' },
    {
      id: 'time',
      enabled: selectedOverlayMetadata.has('time'),
      icon: 'clock',
      value: timeAgo(novel.chapters.last_online_update),
      title: `Updated : ${novel.chapters.last_online_update}`
    },
    { id: 'not_downloaded', enabled: true, icon: 'world-www', value: novel.chapters.diff, title: 'Not downloaded chapters' },
    { id: 'novel_id', enabled: false, icon: 'id', value: novel.id, title: 'Novel ID' },
    { id: 'novel_title', enabled: false, icon: 'book', value: novel.title, title: 'Novel Title' },
    { id: 'cover_file', enabled: false, icon: 'photo', value: novel.cover.url, title: 'Cover file' },
    { id: 'author', enabled: false, icon: 'user', value: novel.author, title: 'Novel Author' },
    { id: 'source', enabled: false, icon: 'world', value: novel.source.name, title: 'Novel Source' },
    {
      id: 'chapters_local',
      enabled: false,
      icon: 'book-2',
      value: novel.chapters.local,
      title: 'Chapters in EPUB, Last Title: ${novel.chapters.lastest_title}'
    },
    {
      id: 'chapters_online',
      enabled: false,
      icon: 'cloud',
      value: novel.chapters.online,
      title: `Chapters on ${novel.source.name}, Latest Chap : ${novel.chapters.last_online_update}`
    },
    { id: 'chapters_new', enabled: false, icon: 'bookmarks', value: novel.chapters.diff, title: 'New Chapters' },
    { id: 'last_sync', enabled: false, icon: 'refresh', value: novel.chapters.last_sync, title: 'Last Sync' },
    { id: 'current_chapter', enabled: false, icon: 'bookmark', value: novel.reading.chapter, title: 'Current Chapter' },
    { id: 'unread_chapters', enabled: false, icon: 'book', value: novel.reading.unread, title: 'Unread Chapters' },
    { id: 'read_progress', enabled: false, icon: 'percentage', value: novel.reading.percent, title: 'Read Progress' },
    { id: 'characters_local', enabled: false, icon: 'user', value: novel.characters.local, title: 'Local Characters' },
    { id: 'characters_online', enabled: false, icon: 'users', value: novel.characters.online, title: 'Online Characters' },
    { id: 'characters_new', enabled: false, icon: 'user-plus', value: novel.characters.new, title: 'New Characters' }
  ];

  const optionalMeta = metaConfig
    .filter(item => item.enabled)
    .map(item => renderMeta(item.icon, item.value, item.title))
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
