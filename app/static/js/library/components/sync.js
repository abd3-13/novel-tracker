export function initSyncPanel() {

    console.log("Sync initialized");

    renderMetadata();

    bindEvents();

    updateSummary();

}

function renderMetadata() {

    const container = document.getElementById("sync-metadata");

    container.innerHTML = `<div class="text-muted">Metadata registry will be loaded here.</div>`;

}

function bindEvents() {

    document
        .querySelectorAll("#sync-offcanvas input")
        .forEach(input => { input.addEventListener("change", updateSummary); });

    document
        .getElementById("sync-start")
        .addEventListener("click", startSync);

}

function updateSummary() {

    const source = document.querySelector("input[name='sync-source']:checked" )?.nextElementSibling.textContent.trim();

    const mode = document.querySelector("input[name='sync-mode']:checked" )?.nextElementSibling.textContent.trim();

    const fields = document.querySelectorAll("#sync-metadata input:checked" ).length;

    document.getElementById("sync-summary-source" ).textContent = source ?? "-";

    document.getElementById("sync-summary-mode" ).textContent = mode ?? "-";

    document.getElementById("sync-summary-fields" ).textContent = fields;

}

function collectJob() {

    return {

        source:
            document.querySelector("input[name='sync-source']:checked")?.value,

        mode:
            document.querySelector("input[name='sync-mode']:checked")?.value,

        dry_run:
            document.getElementById("sync-dry-run").checked,

        force:
            document.getElementById("sync-force").checked,

        fields: []

    };

}

function startSync() {

    const job = collectJob();

    console.log(job);

}
