const IMPORT_ROW_STORAGE_KEY = 'library.importRowMetadata';

export const IMPORT_METADATA = [
  {
    id: 'author',
    label: 'Author',
    icon: 'user',
    default: true,
    getValue: candidate => candidate.author
  },
  {
    id: 'chapters',
    label: 'Chapters',
    icon: 'book-2',
    default: true,
    getValue: candidate => (candidate.chapters ? `${candidate.chapters} chapters` : '')
  },
  {
    id: 'source',
    label: 'Source',
    icon: 'world',
    default: true,
    getValue: candidate => candidate.source
  },
  {
    id: 'characters',
    label: 'Characters',
    icon: 'users',
    default: true,
    getValue: candidate => (candidate.characters ? `${candidate.characters} characters` : '')
  },
  {
    id: 'description',
    label: 'Description',
    icon: 'align-left',
    getValue: candidate => candidate.description
  },
  {
    id: 'url',
    label: 'Source URL',
    icon: 'link',
    getValue: candidate => candidate.url
  },
  {
    id: 'last_chapter',
    label: 'Last chapter',
    icon: 'bookmark',
    getValue: candidate => candidate.last_title
  },
  {
    id: 'last_chapter_file',
    label: 'Last chapter file',
    icon: 'file-code',
    getValue: candidate => candidate.last_file
  },
  {
    id: 'cover_file',
    label: 'Cover file',
    icon: 'photo',
    getValue: candidate => candidate.cover_id
  }
];

const IMPORT_METADATA_IDS = new Set(IMPORT_METADATA.map(metadata => metadata.id));

const DEFAULT_IMPORT_METADATA = IMPORT_METADATA.filter(metadata => metadata.default).map(
  metadata => metadata.id
);

export function getSelectedImportMetadata() {
  let stored = null;

  try {
    stored = localStorage.getItem(IMPORT_ROW_STORAGE_KEY);
  } catch {
    return [...DEFAULT_IMPORT_METADATA];
  }

  if (!stored) {
    return [...DEFAULT_IMPORT_METADATA];
  }

  try {
    const parsed = JSON.parse(stored);

    if (!Array.isArray(parsed)) {
      return [...DEFAULT_IMPORT_METADATA];
    }

    const selected = parsed.filter(id => IMPORT_METADATA_IDS.has(id));

    return selected.length ? selected : [...DEFAULT_IMPORT_METADATA];
  } catch {
    return [...DEFAULT_IMPORT_METADATA];
  }
}

export function saveSelectedImportMetadata(ids) {
  try {
    localStorage.setItem(IMPORT_ROW_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Storage can be unavailable in private browsing; keep the defaults.
  }
}

export function getSelectedImportMetadataDefinitions() {
  const selected = new Set(getSelectedImportMetadata());

  return IMPORT_METADATA.filter(metadata => selected.has(metadata.id));
}

export function buildImportDetail(candidate, definitions = getSelectedImportMetadataDefinitions()) {
  return definitions
    .map(metadata => metadata.getValue(candidate))
    .map(value => String(value ?? '').trim())
    .filter(Boolean)
    .join(' · ');
}
