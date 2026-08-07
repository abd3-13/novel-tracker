// static/js/library/state.js

export const library = {
  // Raw data from the API
  novels: [],

  // Current working set after search/filter/sort
  visible: [],

  // Selected novels
  ids: [],

  // UI State
  search: '',
  sort: {
    id: 'title',
    label: 'Title',
    field: 'title',
    direction: 'asc',
    icon: 'sort-a-z',
    group: 'Novel'
  },

  // Active filters
  filters: [],
  filterExpanded: 0,
  matchMode: 'all',

  // Selection
  selected: [],

  // Statistics
  stats: {
    total: 0,
    unread: 0,
    missingEpub: 0,
    updates: 0
  }
};
