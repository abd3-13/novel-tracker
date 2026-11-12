// static/js/library/api.js

async function checkServer() {
  const status = document.querySelector("#tile_server_stat .status");

  if (!status) return;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1500);

  try {
    const response = await fetch("/status", {
      cache: "no-store",
      signal: controller.signal
    });

    if (!response.ok) throw new Error("Server down");

    status.classList.remove("status-red");
    status.classList.add("status-green");
    status.title = "Backend Server is reachable";
  } catch {
    status.classList.remove("status-green");
    status.classList.add("status-red");
    status.title = "Backend Server is UNreachable";
  } finally {
    clearTimeout(timeout);
  }
}

export function initServerStatus() {
  checkServer();
  setInterval(checkServer, 2000);
}

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

export async function deleteMissingEpubs() {
  const response = await fetch('/api/v1/library/missing-epub', {
    method: 'DELETE'
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.message || 'Failed to clean up missing EPUB records.');
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

export function listenImportScan(handlers = {}) {
  const source = new EventSource('/api/v1/import/scan/events');

  let completed = false;

  source.addEventListener('progress', event => {
    handlers.progress?.(JSON.parse(event.data));
  });

  source.addEventListener('done', event => {
    completed = true;

    handlers.done?.(JSON.parse(event.data));

    source.close();
  });

  source.addEventListener('scan_error', event => {
    completed = true;

    const data = JSON.parse(event.data);

    handlers.error?.(new Error(data.message || 'Failed to scan the EPUB directory.'));

    source.close();
  });

  source.onerror = error => {
    if (completed) {
      // Expected because the stream has been closed.
      return;
    }

    console.error('Import scan event stream error:', error);

    handlers.error?.(new Error('Lost connection to the scan.'));

    source.close();
  };

  return source;
}

export async function scanImport() {
  const response = await fetch('/api/v1/import/scan', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  });

  const result = await response.json();

  if (!response.ok || !result.success) {
    throw new Error(result.message || `Failed to scan EPUBs (${response.status}).`);
  }

  return result;
}

export async function importEpubs(filenames) {
  const response = await fetch('/api/v1/import', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ filenames })
  });

  const result = await response.json();

  if (!response.ok || !result.success) {
    throw new Error(result.message || `Failed to import EPUBs (${response.status}).`);
  }

  return result;
}

export async function streamImport(filenames, handlers = {}, signal) {
  const response = await fetch('/api/v1/import/events', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ filenames }),
    signal
  });

  if (!response.ok) {
    let message = `Failed to import EPUBs (${response.status}).`;

    try {
      const result = await response.json();

      if (result.message) message = result.message;
    } catch {
      // Non-JSON error response.
    }

    throw new Error(message);
  }

  if (!response.body) {
    throw new Error('Streaming is not supported by this browser.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const dispatch = line => {
    if (!line.trim()) return;

    let payload;

    try {
      payload = JSON.parse(line);
    } catch {
      console.error('Invalid import stream line:', line);
      return;
    }

    handlers[payload.event]?.(payload.data);
  };

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    lines.forEach(dispatch);
  }

  buffer += decoder.decode();

  if (buffer.trim()) dispatch(buffer);
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
