export function initSyncPanel() {
  console.log("Sync initialized");

  renderMetadata();

  bindEvents();

  updateSummary();
}

async function renderMetadata() {
  const container = document.getElementById("sync-metadata");

  container.innerHTML = `<div class="text-center py-4"><div class="spinner-border spinner-border-sm text-muted"></div></div>`;

  try {
    const response = await fetch("/api/sync/registry");

    if (!response.ok) throw new Error("Failed to load metadata registry.");

    const fields = await response.json();

    container.innerHTML = `
      <label class="form-check mb-3">
        <input class="form-check-input" id="sync-select-all" type="checkbox" checked>
        <span class="form-check-label fw-semibold">Select All</span>
      </label>
      ${fields
        .map(
          (field) => `
          <label class="form-check mb-3">
              <input class="form-check-input sync-field" type="checkbox" value="${field.id}" ${field.default ? "checked" : ""}>
              <div class="form-check-label">
                  <div class="d-flex align-items-center">
                      <i class="ti ti-${field.icon} me-2 text-muted"></i>
                      <span>${field.name}</span>
                      <span class="ms-2">
                          ${field.providers.includes("local") ? `<span class="badge bg-blue-lt"><i class="ti ti-file text-muted"></i></span>` : ""}
                          ${field.providers.includes("online") ? `<span class="badge bg-green-lt"><i class="ti ti-world text-muted"></i></span>` : ""}
                      </span>
                  </div>
                  <div class="text-muted small ms-4">${field.description}</div>
              </div>
          </label>
      `,
        )
        .join("")}
      `;

    document
      .getElementById("sync-select-all")
      .addEventListener("change", (e) => {
        document
          .querySelectorAll(".sync-field")
          .forEach((cb) => (cb.checked = e.target.checked));

        updateSummary();
      });

    document.querySelectorAll(".sync-field").forEach((cb) => {
      cb.addEventListener("change", updateSummary);
    });
  } catch (err) {
    console.error(err);
    container.innerHTML = `<div class="alert alert-danger mb-0"><i class="ti ti-alert-circle me-2"></i>Failed to load synchronization metadata.</div>`;
  }
}

function bindEvents() {
  document.querySelectorAll("#sync-offcanvas input").forEach((input) => {
    input.addEventListener("change", updateSummary);
  });

  document.getElementById("sync-start").addEventListener("click", startSync);
}

function updateSummary() {
  const source = document
    .querySelector("input[name='sync-source']:checked")
    ?.nextElementSibling.textContent.trim();

  const mode = document
    .querySelector("input[name='sync-mode']:checked")
    ?.nextElementSibling.textContent.trim();

  const fields = document.querySelectorAll(
    "#sync-metadata input:checked",
  ).length;

  document.getElementById("sync-summary-source").textContent = source ?? "-";

  document.getElementById("sync-summary-mode").textContent = mode ?? "-";

  document.getElementById("sync-summary-fields").textContent = fields;
}

function collectJob() {
  return {
    source: document.querySelector("input[name='sync-source']:checked")?.value,

    mode: document.querySelector("input[name='sync-mode']:checked")?.value,

    dry_run: document.getElementById("sync-dry-run").checked,

    force: document.getElementById("sync-force").checked,

    fields: [],
  };
}

function startSync() {
  const job = collectJob();

  console.log(job);
}
