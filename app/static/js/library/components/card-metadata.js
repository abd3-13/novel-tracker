import { timeAgo } from './../utils.js';

export const CARD_METADATA = [
  {
    id: 'characters',
    label: 'Characters',
    icon: 'users',
    overlay: true,
    overlayDefault: true,
    getValue: novel => `${novel.characters.local}/${novel.characters.online}`,
    getTitle: novel => `Characters: Local - ${novel.characters.local} | Online - ${novel.characters.online}`
  },
  {
    id: 'progress',
    label: 'Read progress',
    icon: 'percentage',
    overlay: true,
    overlayDefault: true,
    getValue: novel => `${novel.reading.percent}%`,
    getTitle: () => 'Read progress %'
  },
  {
    id: 'chapter',
    label: 'Current chapter',
    icon: 'bookmark',
    overlay: true,
    overlayDefault: true,
    getValue: novel => novel.reading.chapter,
    getTitle: novel => `Currently on Ch${novel.reading.chapter}`
  },
  {
    id: 'updates',
    label: 'New chapters',
    icon: 'bookmarks',
    overlay: true,
    overlayDefault: true,
    getValue: novel => novel.chapters.diff,
    getTitle: () => 'New chapters'
  },
  {
    id: 'time',
    label: 'Last update',
    icon: 'clock',
    overlay: true,
    overlayDefault: true,
    getValue: novel => timeAgo(novel.chapters.last_online_update),
    getTitle: novel => `Updated: ${novel.chapters.last_online_update}`
  },

  {
    id: 'novel_id',
    label: 'Novel ID',
    icon: 'id',
    overlay: true,
    getValue: novel => novel.id,
    getTitle: () => 'Novel ID'
  },
  {
    id: 'novel_title',
    label: 'Novel Title',
    icon: 'book',
    overlay: true,
    getValue: novel => novel.title,
    getTitle: () => 'Novel Title'
  },
  {
    id: 'cover_file',
    label: 'Cover file',
    icon: 'photo',
    overlay: true,
    getValue: novel => novel.cover.url,
    getTitle: () => 'Cover file'
  },
  {
    id: 'author',
    label: 'Novel Author',
    icon: 'user',
    overlay: true,
    getValue: novel => novel.author,
    getTitle: () => 'Novel Author'
  },
  {
    id: 'source',
    label: 'Novel Source',
    icon: 'world',
    overlay: true,
    getValue: novel => novel.source.name,
    getTitle: () => 'Novel Source'
  },
  {
    id: 'chapters_local',
    label: 'Chapters in EPUB',
    icon: 'book-2',
    overlay: true,
    getValue: novel => novel.chapters.local,
    getTitle: novel => `Chapters in EPUB, Last Title: ${novel.chapters.lastest_title}`
  },
  {
    id: 'chapters_online',
    label: 'Chapters online',
    icon: 'cloud',
    overlay: true,
    getValue: novel => novel.chapters.online,
    getTitle: novel => `Chapters on ${novel.source.name}, Latest Chap: ${novel.chapters.last_online_update}`
  },
  {
    id: 'last_sync',
    label: 'Last sync',
    icon: 'refresh',
    overlay: true,
    getValue: novel => novel.chapters.last_sync,
    getTitle: () => 'Last Sync'
  },
  {
    id: 'current_chapter',
    label: 'Current Chapter',
    icon: 'bookmark',
    overlay: true,
    getValue: novel => novel.reading.chapter,
    getTitle: () => 'Current Chapter'
  },
  {
    id: 'unread_chapters',
    label: 'Unread Chapters',
    icon: 'book',
    overlay: true,
    getValue: novel => novel.reading.unread,
    getTitle: () => 'Unread Chapters'
  },
  {
    id: 'characters_new',
    label: 'New Characters',
    icon: 'user-plus',
    overlay: true,
    getValue: novel => novel.characters.new,
    getTitle: () => 'New Characters'
  }
];
