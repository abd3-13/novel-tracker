// static/js/cover.js

// Shared between the login page (where the preference is chosen) and the
// library views (where it is applied).

export const COVER_MODE_KEY = 'library.coverMode';

export const COVER_MODE = {
  DEFAULT: 'default',
  NOVEL: 'novel'
};

export const DEFAULT_COVER_SRC = 'static/img/cover/cover.webp';

const COVER_DIR = 'static/img/cover/';

export function getCoverMode() {
  try {
    return localStorage.getItem(COVER_MODE_KEY) === COVER_MODE.NOVEL ? COVER_MODE.NOVEL : COVER_MODE.DEFAULT;
  } catch {
    return COVER_MODE.DEFAULT;
  }
}

export function setCoverMode(mode) {
  const value = mode === COVER_MODE.NOVEL ? COVER_MODE.NOVEL : COVER_MODE.DEFAULT;

  try {
    localStorage.setItem(COVER_MODE_KEY, value);
  } catch {
    // Storage can be unavailable (private mode, blocked cookies); the UI still
    // reflects the choice for this page load.
  }

  return value;
}

export function getNovelCoverSrc(novel, mode = getCoverMode()) {
  if (mode !== COVER_MODE.NOVEL) return DEFAULT_COVER_SRC;

  const file = novel?.cover?.url;

  if (!novel?.cover?.exists || !file) return DEFAULT_COVER_SRC;

  return `${COVER_DIR}${file}`;
}
