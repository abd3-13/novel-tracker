import { fetchEPUB } from './../api.js';

const DEBUG = false;
const log = (...args) => DEBUG && console.log(...args);

const settings = window.librarySettings || {};

export function openNovelReader(novelID) {
  if (!ePub) {
    console.error('epub.js not loaded');
    return;
  }

  initTocPanel();
  loadEPUB(novelID);
}

let tocPanelWired = false;

/**
 * Wires the floating TOC panel's open/close behavior once. Idempotent via
 * `tocPanelWired` — the modal markup itself isn't recreated per book load
 * (only #epub-viewer's contents are), so this only needs to run once.
 */
function initTocPanel() {
  if (tocPanelWired) return;

  const toggle = document.getElementById('epub-toc-toggle');
  const panel = document.getElementById('epub-toc-panel');
  const backdrop = document.getElementById('epub-toc-backdrop');

  if (!toggle || !panel || !backdrop) return;

  const setOpen = open => {
    panel.classList.toggle('show', open);
    backdrop.classList.toggle('show', open);
    panel.setAttribute('aria-hidden', String(!open));
    toggle.setAttribute('aria-expanded', String(open));
  };

  toggle.addEventListener('click', () => {
    setOpen(!panel.classList.contains('show'));
  });

  backdrop.addEventListener('click', () => setOpen(false));

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && panel.classList.contains('show')) {
      setOpen(false);
    }
  });

  // Close after picking a chapter. The separate delegated TOC click
  // handler (registered per-load, further down) still fires
  // epubRendition.display() — this just also collapses the panel.
  panel.addEventListener('click', event => {
    if (event.target.closest('button[data-href]')) {
      setOpen(false);
    }
  });

  tocPanelWired = true;
}

let epubBook = null;
let epubRendition = null;
let epubTOC = [];
let tocByHref = new Map(); // href (no fragment) -> { item, button }
let loadToken = 0; // guards against out-of-order concurrent loads

async function loadEPUB(novelID) {
  const viewer = document.getElementById('epub-viewer');

  if (!viewer) {
    console.error('EPUB viewer element was not found.');
    return;
  }

  const myToken = ++loadToken;

  const titleEl = document.getElementById('epub-book-title');
  const authorEl = document.getElementById('epub-book-author');
  if (titleEl) titleEl.textContent = 'Loading…';
  if (authorEl) authorEl.textContent = '';

  viewer.innerHTML = `
    <div class="d-flex align-items-center justify-content-center w-100 h-100 text-center">
      <h1 class="mb-0">
        Loading
        <span class="animated-dots"></span>
      </h1>
    </div>
  `;

  try {
    const arrayBuffer = await fetchEPUB(novelID);

    // A newer load started while we were fetching — abandon this one.
    if (myToken !== loadToken) return;

    log(`EPUB downloaded: ${arrayBuffer.byteLength} bytes`);

    if (epubRendition) { epubRendition.destroy();  epubRendition = null; }

    viewer.innerHTML = '';

    epubBook = ePub(arrayBuffer);

    await epubBook.ready;

    if (myToken !== loadToken) return;

    log('EPUB parsed successfully:', epubBook);

    epubBook.loaded.metadata.then(metadata => { if (myToken !== loadToken) return; updateBookMetadata(metadata); });

    // EPUBs are untrusted input. Allowing scripts here would let a crafted
    // book run JavaScript in the application's origin and read the session.
    epubRendition = epubBook.renderTo(viewer, {width: '100%', height: '100%', flow: 'scrolled', allowScriptedContent: false});

    await epubBook.loaded;

    if (myToken !== loadToken) return;

    /*
     * Build the table of contents once, with an href -> {item, button}
     * map so relocation updates are O(1) instead of re-scanning the DOM.
     * Uses event delegation instead of one listener per item.
     */

    const toc = await epubBook.loaded.navigation;

    if (myToken !== loadToken) return;

    log('EPUB navigation has been loaded now');

    epubTOC = toc;

    const tocContainer = document.getElementById('epub-toc');

    if (tocContainer) {
      tocContainer.innerHTML = '';
      tocByHref = new Map();

      const fragment = document.createDocumentFragment();
      let flatIndex = 0;

      // epub.js navigation.toc is a tree: each item can have its own
      // `subitems` array of the same shape. Walk it recursively so
      // nested chapters/sections show up, not just the top level.
      const renderItems = (items, depth) => {
        items.forEach(item => {
          const button = document.createElement('button');

          button.className = 'list-group-item list-group-item-action';
          button.textContent = item.label.replace('Chapter ', '').trim();
          button.style.paddingLeft = `${1 + depth * 1.25}rem`;

          button.dataset.href = item.href;
          button.dataset.index = flatIndex++;
          button.dataset.depth = depth;

          fragment.appendChild(button);
          tocByHref.set(normalizeHref(item.href), { item, button });

          if (Array.isArray(item.subitems) && item.subitems.length > 0) {
            renderItems(item.subitems, depth + 1);
          }
        });
      };

      renderItems(toc, 0);
      tocContainer.appendChild(fragment);
    }

    // Single delegated click handler for the whole TOC.
    if (tocContainer && !tocContainer.dataset.delegated) {
      tocContainer.addEventListener('click', async event => {
        const button = event.target.closest('button[data-href]');

        if (!button || !epubRendition) return;
        
        try {
          await epubRendition.display(button.dataset.href);
        } catch {
          await epubRendition.display(`Text/${button.dataset.href}`);
        }
      });

      tocContainer.dataset.delegated = 'true';
    }

    /*
     * Whenever EPUB.js changes location, update:
     *
     * 1. Current chapter text
     * 2. Active TOC button
     */
    epubRendition.on('relocated', location => {
      updateCurrentChapter(location);
    });

    /*
     * Display EPUB based on the reader setting.
     *
     * EPUB_READER_FROM:
     *
     * "1" -> beginning of the EPUB
     * "0" -> last chapter in the EPUB
     */

    const epubFromStart = settings.EPUB_READER_FROM ?? "1";
    const lastChapter = epubFromStart === "0" ? getLastTOCItem(epubTOC.toc) : null;
    
    if (!lastChapter?.href) {
      if (epubFromStart === "0") {
        console.warn("Could not determine the last EPUB chapter; opening from the beginning.");
      }
    
      await epubRendition.display();
    } else {
      try {
        await epubRendition.display(lastChapter.href);
      } catch {
        await epubRendition.display(`Text/${lastChapter.href}`);
      }
    }
    

    if (myToken !== loadToken) return;

    applyReaderTheme();
  } catch (error) {
    if (myToken !== loadToken) return; // a newer load superseded this failure

    console.error('Failed to load EPUB:', error);

    viewer.innerHTML = `
      <div class="text-center">
        <i class="ti ti-alert-circle text-danger icon icon-lg mb-3"></i>

        <h3>Unable to load EPUB</h3>

        <p class="text-secondary mb-0">The book could not be loaded.</p>
      </div>
    `;
  }
}

/**
 * epub.js renders content inside an isolated iframe, so Tabler's stylesheet
 * and CSS custom properties (--tblr-*) never reach it — var(--tblr-x) inside
 * a theme rule resolves to nothing. Instead, read the *resolved* values from
 * the parent document at call time and inject them as literals. This also
 * means it keeps matching Tabler's light/dark mode as long as you re-call it
 * after a theme toggle (e.g. from your dark-mode switch handler).
 */
function applyReaderTheme() {
  if (!epubRendition) return;

  const bodyStyle = getComputedStyle(document.body);
  const fontFamily = bodyStyle.fontFamily || 'sans-serif';
  const textColor = bodyStyle.color || '#ccc';

  epubRendition.themes.default({
    html: {
      background: '#1f2937 !important'
    },
    body: {
      margin: '10px',
      padding: '5px !important',
      background: 'transparent !important',
      color: `${textColor} !important`,
      'font-family': `${fontFamily} !important`
    },
    'p, span, div, li, a': {
      'font-family': 'inherit !important'
    }
  });
}

/**
 * Returns the last navigable item in the EPUB TOC.
 *
 * If the final TOC item contains nested subitems, the deepest
 * final item is considered the last chapter.
 */
function getLastTOCItem(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  const lastItem = items[items.length - 1];

  if (Array.isArray(lastItem.subitems) && lastItem.subitems.length > 0) {
    return getLastTOCItem(lastItem.subitems);
  }

  return lastItem;
}


/**
 * epub.js resolves package metadata (OPF <metadata>) via book.loaded.metadata.
 * Field names follow the OPF/Dublin Core spec: `title` and `creator`
 * (not `author`) — https://github.com/futurepress/epub.js docs call this out.
 * Uses textContent, not innerHTML: this string comes from the EPUB file
 * itself, which is untrusted content, not something we control.
 */
function updateBookMetadata(metadata) {
  const titleEl = document.getElementById('epub-book-title');
  const authorEl = document.getElementById('epub-book-author');

  if (titleEl) {
    titleEl.textContent = metadata?.title?.trim() || 'Untitled';
  }

  if (authorEl) {
    authorEl.textContent = metadata?.creator?.trim() || 'Unknown author';
  }
}

/**
 * Update the reader UI to match the current EPUB location.
 * Resolves the active TOC entry directly from the location's href
 * instead of relying on click-tracked state, so scroll/swipe/programmatic
 * navigation stays in sync too.
 */
let activeButton = null;

function updateCurrentChapter(location) {
  if (!location || !location.start) {
    return;
  }
  log(location);

  const currentHref = normalizeHref(location.start.href);

  const entry = tocByHref.get(currentHref);

  const currentChapter = document.getElementById('current-chapter');
  if (currentChapter && entry) {
    currentChapter.textContent = entry.item.label;
  }

  if (activeButton) {
    activeButton.classList.remove('active');
  }

  if (entry) {
    entry.button.classList.add('active');
    activeButton = entry.button;
  }
}

/**
 * EPUB.js can return hrefs with fragments.
 * Strip the fragment so TOC and rendition locations
 * can be compared reliably.
 */
function normalizeHref(href) {
  if (!href) {
    return '';
  }

  return href.split('#')[0];
}
