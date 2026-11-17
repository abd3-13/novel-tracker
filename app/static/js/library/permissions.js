// static/js/library/permissions.js
//
// The server is the source of truth for authorization. These flags only keep
// the UI from offering actions that would be rejected with 403.

const user = window.libraryUser || {};

export const ROLE = user.role || '';
export const IS_ADMIN = ROLE === 'admin';
export const CAN_EDIT = IS_ADMIN || ROLE === 'user';
export const IS_DEMO = ROLE === 'demo';
