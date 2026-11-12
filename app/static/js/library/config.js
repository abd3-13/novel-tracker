export const STATUS_STYLE = {
  Reading: {
    bg: 'bg-yellow',
    text: 'text-black'
  },
  Completed: {
    bg: 'bg-green',
    text: 'text-black'
  },
  Hiatus: {
    bg: 'bg-purple',
    text: 'text-black'
  },
  Dropped: {
    bg: 'bg-red',
    text: 'text-black'
  },
  Planned: {
    bg: 'bg-secondary',
    text: 'text-black'
  }
};

export const SYNC_TEXT = {
  waiting: 'Waiting...',
  preparing: 'Preparing synchronization',
  synchronize: 'Synchronize',
  synchronizing: 'Synchronizing...',
  complete: 'Synchronization Complete',
  finished: 'Synchronization finished.',
  currentNovel: 'Synchronizing %name%...',
  completedWithErrors: 'Completed with errors',
  completedWithWarnings: 'Completed with warnings',
  updated: 'Updated',
  skipped: 'Skipped',
  fetching: 'Fetching data...',
  metadata: 'Synchronizing metadata...',
  commit: 'Saving changes...',
  done: 'Finishing...',
  cancelled: 'Synchronization Cancelled',
  cancelledMessage: '%count% novel(s) were processed before cancellation.',
  cancelledNotice: 'Synchronization cancelled.'
};

export const LOGIN_TEXT = {
  signingIn: 'Signing in...',
  login: 'Login',
  loginFailed: 'Unable to communicate with the server.',
  connectionError: 'Connection Error'
};

export const FILTER_TEXT = {
  match: 'Match',
  all: 'All',
  any: 'Any',
  conditions: 'Conditions',
  addCondition: 'Add Condition',
  noFilters: 'No filters',
  noFiltersHint: 'Click "Add Condition" to start filtering your library.',
  field: 'Field',
  operator: 'Operator',
  value: 'Value',
  emptyValue: '—',
  delete: 'Delete',
  nullSummary: '—'
};

export const SELECTION_TEXT = {
  selected: '{count} selected',
  between: 'Between',
  selectAll: 'Select all',
  clear: 'Clear',
  done: 'Done'
};

export const TOOLBAR_TEXT = {
  searchPlaceholder: 'Search novels...(title, description, tags, author, notes)',
  sort: 'Sort',
  filter: 'Filter',
  import: 'Import',
  synchronize: 'Synchronize',
  select: 'Select',
  actions: 'Actions',
  searchIcon: 'Search'
};

export const IMPORT_TEXT = {
  scanning: 'Scanning EPUBs...',
  scanFailed: 'Failed to scan the EPUB directory.',
  importFailed: 'Failed to import the selected EPUBs.',
  noNew: 'No new EPUBs found in the source directory.',
  imported: 'Imported',
  skipped: 'Skipped',
  failed: 'Failed',
  new: 'New',
  alreadyExists: 'Already exists',
  error: 'Error',
  importAll: 'Import All',
  import: 'Import'
};

export const SYNC_BUTTON_STATES = {
  idle: {
    disabled: false,
    html: '<i class="ti ti-refresh me-1"></i> Synchronize'
  },
  loading: {
    disabled: true,
    html: '<span class="spinner-border spinner-border-sm me-1"></span> Synchronizing...'
  },
  success: {
    disabled: true,
    html: '<i class="ti ti-check me-1"></i> Synchronized'
  },
  error: {
    disabled: true,
    html: '<i class="ti ti-alert-circle me-1"></i> Failed'
  }
};

export const SYNC_CANCEL_BUTTON_STATES = {
  idle: {
    disabled: false,
    html: '<i class="ti ti-player-stop me-1"></i> Cancel Synchronization'
  },
  cancelling: {
    disabled: true,
    html: '<span class="spinner-border spinner-border-sm me-1"></span> Cancelling...'
  },
  done: {
    disabled: true,
    html: '<i class="ti ti-check me-1"></i> Cancelled'
  }
};

export const FILTER_FIELDS = [
  {
    category: 'Chapters',
    items: [
      {
        field: 'unread',
        label: 'Unread',
        type: 'number',
        editor: 'number',
        icon: 'book-2',
        getter: novel => novel.reading.unread
      },
      {
        field: 'progress',
        label: 'Read Progress',
        type: 'number',
        editor: 'number',
        icon: 'progress',
        getter: novel => novel.reading.percent
      },
      {
        field: 'local',
        label: 'Local Chapters',
        type: 'number',
        editor: 'number',
        icon: 'books',
        getter: novel => novel.chapters.local
      },
      {
        field: 'online',
        label: 'Online Chapters',
        type: 'number',
        editor: 'number',
        icon: 'books',
        getter: novel => novel.chapters.online
      },
      {
        field: 'currentChapter',
        label: 'Current Chapter',
        type: 'number',
        editor: 'number',
        icon: 'bookmark',
        getter: novel => novel.reading.chapter
      }
    ]
  },

  {
    category: 'Updates',
    items: [
      {
        field: 'updates',
        label: 'Updates',
        type: 'number',
        editor: 'number',
        icon: 'bell',
        getter: novel => novel.chapters.diff
      },
      {
        field: 'lastChapter',
        label: 'Last Chapter Time',
        type: 'date',
        editor: 'date',
        icon: 'clock',
        getter: novel => novel.chapters.last_online_update
      }
    ]
  },

  {
    category: 'Characters',
    items: [
      {
        field: 'localCharacters',
        label: 'Local Characters',
        type: 'number',
        editor: 'number',
        icon: 'users',
        getter: novel => novel.characters.local
      },
      {
        field: 'onlineCharacters',
        label: 'Online Characters',
        type: 'number',
        editor: 'number',
        icon: 'users',
        getter: novel => novel.characters.online
      },
      {
        field: 'newCharacters',
        label: 'New Characters',
        type: 'number',
        editor: 'number',
        icon: 'users-plus',
        getter: novel => novel.characters.new
      }
    ]
  },

  {
    category: 'File',
    items: [
      {
        field: 'epubExists',
        label: 'EPUB Exists',
        type: 'enum',
        editor: 'select',
        icon: 'file-check',
        values: ['Available', 'Missing'],
        getter: novel => (novel.epub.exists ? 'Available' : 'Missing')
      }
    ]
  },

  {
    category: 'Novel',
    items: [
      {
        field: 'title',
        label: 'Title',
        type: 'string',
        editor: 'text',
        icon: 'sort-a-z',
        getter: novel => novel.title
      },
      {
        field: 'author',
        label: 'Author',
        type: 'string',
        editor: 'text',
        icon: 'user',
        getter: novel => novel.author
      },
      {
        field: 'status',
        label: 'Status',
        type: 'enum',
        editor: 'select',
        icon: 'circle-check',
        values: ['Reading', 'Completed', 'Hiatus', 'Dropped'],
        getter: novel => novel.status
      },
      {
        field: 'tags',
        label: 'Tags',
        type: 'string',
        editor: 'text',
        icon: 'tags',
        getter: novel => novel.tags
      },
      {
        field: 'source',
        label: 'Source',
        type: 'string',
        editor: 'text',
        icon: 'world',
        getter: novel => novel.source.name
      }
    ]
  }
];

export const FILTER_MAP = new Map(FILTER_FIELDS.flatMap(group => group.items).map(field => [field.field, field]));

export const SORT_OPTIONS = [
  {
    group: 'Chapters',
    items: [
      { field: 'unread', label: 'Unread', direction: 'desc', icon: 'book-2' },
      { field: 'progress', label: 'Read Progress', direction: 'desc', icon: 'progress' },
      { field: 'online', label: 'Online Chapters', direction: 'desc', icon: 'books' },
      { field: 'local', label: 'Local Chapters', direction: 'desc', icon: 'books' }
    ]
  },
  {
    group: 'Updates',
    items: [
      { field: 'updates', label: 'Updates', direction: 'desc', icon: 'bell' },
      { field: 'lastChapter', label: 'Last Chapter Time', direction: 'desc', icon: 'clock' }
    ]
  },
  {
    group: 'Characters',
    items: [
      { field: 'newCharacters', label: 'New Characters', direction: 'desc', icon: 'users-plus' },
      { field: 'characters', label: 'Local Characters', direction: 'desc', icon: 'users' },
      { field: 'onlineCharacters', label: 'Online Characters', direction: 'desc', icon: 'cloud' }
    ]
  },
  {
    group: 'File',
    items: [
      { field: 'epubExists', label: 'EPUB Exists', direction: 'desc', icon: 'file-check' }
    ]
  },
  {
    group: 'Novel',
    items: [
      { field: 'title', label: 'Title', direction: 'asc', icon: 'sort-a-z' },
      { field: 'author', label: 'Author', direction: 'asc', icon: 'user' },
      { field: 'source', label: 'Source', direction: 'asc', icon: 'world' },
      { field: 'status', label: 'Status', direction: 'asc', icon: 'circle-check' }
    ]
  }
];

export const OPERATORS = {
  '=': (a, b) => a == b,

  '!=': (a, b) => a != b,

  '>': (a, b) => a > b,

  '<': (a, b) => a < b,

  '>=': (a, b) => a >= b,

  '<=': (a, b) => a <= b,

  contains: (a, b) => String(a).toLowerCase().includes(String(b).toLowerCase()),

  'not contains': (a, b) => !String(a).toLowerCase().includes(String(b).toLowerCase()),

  'starts with': (a, b) => String(a).toLowerCase().startsWith(String(b).toLowerCase()),

  'ends with': (a, b) => String(a).toLowerCase().endsWith(String(b).toLowerCase())
};

export const TYPE_OPERATORS = {
  string: ['=', '!=', 'contains', 'not contains', 'starts with', 'ends with'],

  number: ['=', '!=', '>', '<', '>=', '<='],

  enum: ['=', '!='],

  date: ['=', '!=', '>', '<', '>=', '<=']
};
