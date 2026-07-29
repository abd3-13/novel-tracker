// static/js/library/api.js

export async function fetchNovels() {
    const response = await fetch("/api/library");

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    const json = await response.json();

    return json.data;
}
