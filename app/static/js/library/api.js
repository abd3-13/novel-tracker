// static/js/library/api.js

function checkServer() {
    const status = document.querySelector("#tile_server_stat .status");
    fetch("/status", { cache: "no-store" })
        .then(response => {
            if (!response.ok) throw new Error("Server down");

            // Server is reachable
            status.classList.remove("status-red");
            status.classList.add("status-green");
            status.title = "Backend Server is reachable";
        })
        .catch(() => {
            // Server is not reachable
            status.classList.remove("status-green");
            status.classList.add("status-red");
            status.title = "Backend Server is UNreachable";
        });
}

// Check every 5 seconds
setInterval(checkServer, 5000);


export async function fetchNovels() {
  const response = await fetch('/api/v1/library');

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const json = await response.json();

  return json.data;
}

export async function fetchNovel(novelId) {
  const response = await fetch(`/api/v1/library/${novelId}`);

  const result = await response.json();

  if (!response.ok) throw new Error(result.message || `Failed to load novel with ID ${novelId}.`);

  return result.data;
}

export async function updateNovel(novelId, updates) {
  const response = await fetch(`/api/v1/library/${novelId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updates)
  });

  const result = await response.json();

  if (!response.ok) throw new Error(result.message || `Failed to update novel with ID ${novelId}.`);

  return result;
}

export async function deleteNovel(novelId) {
  const response = await fetch(`/api/v1/library/${novelId}`, {
    method: 'DELETE'
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.message || `Failed to delete novel with ID ${novelId}.`);
  }

  return result;
}

export async function fetchEPUB(novelID) {
   const epubURL = `/api/v1/epub/${novelID}`;

    const response = await fetch(epubURL, {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        Accept: 'application/epub+zip'
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to load EPUB: HTTP ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();

    if (!arrayBuffer || arrayBuffer.byteLength === 0) {
      throw new Error('The EPUB response is empty.');
    }

  return arrayBuffer;
}

export async function fetchSyncMetadata() {
  const response = await fetch('/api/v1/sync/registry');

  if (!response.ok) throw new Error('Failed to load metadata registry. ERROR : ${response.status}');

  const fields = await response.json();

  return fields;
}

export async function getSyncRegistry() {
  const response = await fetch('/api/v1/sync/registry');

  if (!response.ok) throw new Error('Failed to load metadata registry.');

  return response.json();
}

export async function runSync(job) {
  const response = await fetch('/api/v1/sync', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(job)
  });

  const result = await response.json();

  if (!response.ok) throw new Error(result.message || result.error || 'Synchronization failed.');

  return result;
}

export async function cancelSync(jobId) {
  const response = await fetch(`/api/v1/sync/${jobId}/cancel`, {
    method: 'POST'
  });

  const result = await response.json();

  if (!response.ok) throw new Error(result.message || result.error || 'Failed to cancel synchronization.');

  return result;
}

export function listenSyncProgress(jobId, handlers = {}) {
  const source = new EventSource(`/api/v1/sync/${jobId}/events`);

  let completed = false;

  const listen = (event, handler) => {
    source.addEventListener(event, e => {
      handler?.(JSON.parse(e.data));
    });
  };

  listen('job_start', handlers.job_start);
  listen('novel_start', handlers.novel_start);
  listen('stage', handlers.stage);
  listen('field', handlers.field);
  listen('novel_finish', handlers.novel_finish);

  source.addEventListener('job_finish', event => {
    completed = true;

    const data = JSON.parse(event.data);

    handlers.job_finish?.(data);

    // The stream has served its purpose.
    source.close();
  });

  source.onerror = error => {
    if (completed) {
      // Expected because the stream has been closed.
      return;
    }

    console.error('Sync event stream error:', error);

    handlers.error?.(error);

    source.close();
  };

  return source;
}

export async function saveSetting(key, value) {
  const response = await fetch('/api/v1/settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ key, value })
  });

  const contentType = response.headers.get('content-type') || '';

  if (!contentType.includes('application/json')) {
    const text = await response.text();
    throw new Error(text || `Failed to save setting "${key}" (${response.status}).`);
  }

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.message || `Failed to save setting "${key}".`);
  }

  return result;
}
