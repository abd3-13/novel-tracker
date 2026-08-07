// static/js/library/api.js

export async function fetchNovels() {
  const response = await fetch('/api/v1/library');

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const json = await response.json();

  return json.data;
}

export async function fetchSyncMetadata() {
  const response = await fetch('/api/v1/sync/registry');

  if (!response.ok) throw new Error('Failed to load metadata registry. ERROR : ${response.status}');

  const fields = await response.json();

  return fields;
}
