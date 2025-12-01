/* novel_tracker.js — AJAX DataTables + actions
   Expects: showToast(message, category) available globally (in index.html)
*/

let dt = null;

document.addEventListener("DOMContentLoaded", () => {
  initTable();
  initModalsAndForms();
  attachGlobalHandlers();
  initEpubFetchButtons();
  enableHoverPopup();
  checkServer();
});

function initTable() {
  dt = new DataTable("#table", {
    ajax: {
      url: "/api/novels",
      dataSrc: "data"
    },
    columns: [
      { data: "id" },
      {
        data: "name",
        render: function (data, type, row) {
          const url = row.url || "#";
          // keep link target blank if no url
          return `<span class="novel-hover"
            data-author="${escapeHtml(row.author || '')}"
            data-desc="${escapeHtml(row.description || '')}"
            data-img="static/img/cover/${escapeHtml(row.cover_path || '')}">
        <a href="${escapeHtml(url)}" target="_blank">${escapeHtml(data)}</a>
      </span>`;
        }
      },
      { data: "localchap", defaultContent: "" },
      { data: "onlinechap", defaultContent: "" },
      {
        // Diff = online - local
        data: null,
        render: function (data, type, row) {
          const local = Number(row.localchap) || 0;
          const online = Number(row.onlinechap) || 0;
          const diff = online - local;
          return diff;
        }
      },
      {
        data: "timeago",
        defaultContent: ""
      },
      { data: "source", defaultContent: "" },
      { data: "status", defaultContent: "" },
      { data: "notes", defaultContent: "" },
      {
        data: null,
        orderable: false,
        searchable: false,
        render: function (data, type, row) {
          // Render action buttons. We'll use data- attributes so handlers have everything.
          return `
            <button class="btn btn-act btn-edit" 
              data-id="${row.id}"
              data-name="${escapeHtml(row.name)}"
              data-url="${escapeHtml(row.url)}"
              data-localchap="${row.localchap}"
              data-onlinechap="${row.onlinechap}"
              data-source="${escapeHtml(row.source)}"
              data-status="${escapeHtml(row.status)}"
              data-notes="${escapeHtml(row.notes)}"
              data-filepath="${escapeHtml(row.filepath)}"
            >✏️</button>
            <button class="btn btn-act btn-update"
              data-id="${row.id}"
              data-name="${escapeHtml(row.name)}"
              data-url="${escapeHtml(row.url)}"
              data-source="${escapeHtml(row.source)}"
              data-localchap="${row.localchap}"
              data-onlinechap="${row.onlinechap}"
              data-filepath="${escapeHtml(row.filepath)}"
            >🔄</button>
            <button class="btn btn-act btn-del"
              data-id="${row.id}"
              data-name="${escapeHtml(row.name)}"
            >🗑</button>
          `;
        }
      }
    ],
    
    layout: {
        topStart: {
            buttons: ['copy', 'csv', {
                extend: 'colvis',
                text: 'Cols'
            }, 'searchBuilder'],
            pageLength: true
        },
        bottomStart: {
            info: true
        }
    },
    columnDefs: [{ visible: false, targets: [0,8] }, { width: '20%', targets: 1 }],
    fixedColumns: {start: 1, end: 1},
    fixedHeader: {header: true},
    lengthMenu: [10, 15, 25, 30, 40, 50, 70, 100, 150, { label: 'All', value: -1 }],
    paging: true,
    pageLength: 20,
    processing: false,
    scrollCollapse: false,
    scrollResize: false,
    scrollX: true,
    scrollY: false,
    stateSave: true,
    responsive: true,
    order: [[1, 'asc']],
    ordering: {
        indicators: true,
        handler: false
    },
    columnControl: [['orderAsc', 'orderDesc', 'orderRemove', 'orderClear', 'spacer', 'search']]

  });
}

// Very small HTML escaper
function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// Global event delegation for table actions
function attachGlobalHandlers() {
  document.body.addEventListener("click", (ev) => {
    const el = ev.target;
    if (el.closest && el.closest(".btn-edit")) {
      const btn = el.closest(".btn-edit");
      openEditModalFromButton(btn);
    } else if (el.closest && el.closest(".btn-del")) {
      const btn = el.closest(".btn-del");
      delete_record(btn);
    } else if (el.closest && el.closest(".btn-update")) {
      const btn = el.closest(".btn-update");
      update_record(btn);
    }
  });

  // Add / UpdateAll / Scan buttons
  const btnUpdAll = document.getElementById("btn-updall");
  if (btnUpdAll) btnUpdAll.addEventListener("click", () => openUpdateModal());

  const btnAdd = document.getElementById("btn-add");
  if (btnAdd) btnAdd.addEventListener("click", () => openAddModal());

  const btnSett = document.getElementById("btn-sett");
  if (btnSett) btnSett.addEventListener("click", () => openSettModal());
}

// Modal helpers and form hooks (simple)
function initModalsAndForms() {
  // Edit Form
  const editForm = document.getElementById("editForm");
  if (editForm) {
    editForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const id = document.getElementById("edit-id").value;
      const formData = new FormData(editForm);
      // POST to /edit/<id>
      try {
        const res = await fetch(`/edit/${id}`, {
          method: "POST",
          body: formData
        });
        const j = await res.json();
        showToast(j.message || "Update submitted — reloading table.", j.category || "success");
        closeEditModal();
        dt.ajax.reload();
      } catch (err) {
        showToast("Edit error: " + err, "error");
      }
    });
  }

  // Update All form
  const updateForm = document.getElementById("updateForm");
  if (updateForm) {
    updateForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const formData = new FormData(updateForm);
      document.body.style.cursor = 'wait';
      try {
        const resp = await fetch("/updateall", {
          method: "POST",
          body: formData
        });
        const j = await resp.json();
        showToast(j.message || "Update all finished", j.category || "info");
        closeUpdateModal();
        document.body.style.cursor = 'default';
        dt.ajax.reload();
      } catch (err) {
        showToast("Update all error: " + err, "error");
      }
    });
  }

  // Add form
  const addForm = document.getElementById("addForm");
   if (addForm) {
    addForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const addData = new FormData(addForm);

      try {
        const resp = await fetch("/add", {
          method: "POST",
          body: addData
        });
        const j = await resp.json();
        showToast(j.message || "Novel added", j.category || "info");
        closeAddModal();
        dt.ajax.reload();
      } catch (err) {
        showToast("Update all error: " + err, "error");
      }
    });
  }
  
  
  // Add form uses normal form POST to /add (server-side). We can't intercept easily; leave as is
  // but if you want AJAX add, we can update it later.
}

/* --- Actions --- */

// Fill and show the Edit modal using button dataset
function openEditModalFromButton(btn) {
  const id = btn.dataset.id;
  document.getElementById("edit-id").value = id || "";
  document.getElementById("input-name").value = btn.dataset.name || "";
  document.getElementById("input-url").value = btn.dataset.url || "";
  document.getElementById("input-lchap").value = btn.dataset.localchap || "";
  document.getElementById("input-ochap").value = btn.dataset.onlinechap || "";
  document.getElementById("input-source").value = btn.dataset.source || "";
  document.getElementById("input-status").value = btn.dataset.status || "";
  document.getElementById("input-notes").value = btn.dataset.notes || "";
  document.getElementById("input-filepath").value = btn.dataset.filepath || "";

  // Show modal (simple)
  openEditModel();
}

// Update a single record (calls /update/<id>?...)

async function update_record(btnOrEl) {
  showToast("Updating...");
  document.body.style.cursor = 'wait';
  const btn = btnOrEl.closest ? btnOrEl.closest("button") : btnOrEl;
  const id = btn.dataset.id;
  const name = btn.dataset.name;
  const url = btn.dataset.url;
  const source = btn.dataset.source;
  const local_chap = btn.dataset.localchap;
  const online_chap = btn.dataset.onlinechap;
  const filepath = btn.dataset.filepath;

  const params = new URLSearchParams({
    name: name || "",
    url: url || "",
    source: source || "",
    local_chap: local_chap || 0,
    online_chap: online_chap || 0,
    filepath: filepath || ""
  });

  try {
    const resp = await fetch(`/update/${encodeURIComponent(id)}?${params.toString()}`);
    console.log(`/update/${encodeURIComponent(id)}?${params.toString()}`);
    const j = await resp.json();
    showToast(j.msg || j.message || "Update result", j.status || "info");
    document.body.style.cursor = 'default';
    dt.ajax.reload();
  } catch (err) {
    showToast("Update error: " + err, "error");
  }
}

// Delete a single record (POST to /delete/<id>)
async function delete_record(btnOrEl) {
  const btn = btnOrEl.closest ? btnOrEl.closest("button") : btnOrEl;
  const id = btn.dataset.id;
  const name = btn.dataset.name || "";

  if (!confirm(`Delete '${name}' (id ${id})?`)) return;

  const form = new FormData();
  form.append("name", name);

  try {
    const resp = await fetch(`/delete/${encodeURIComponent(id)}`, {
      method: "POST",
      body: form
    });
    const j = await resp.json();
    if (j.status === "success") {
      showToast(j.msg || "Deleted", "success");
      dt.ajax.reload();
    } else {
      showToast(j.msg || "Delete failed", "error");
    }
  } catch (err) {
    showToast("Delete error: " + err, "error");
  }
}

// Get infos from epub
// Map JSON keys to input IDs
const fieldMap = {
    title: 'input-name',
    source: 'input-source',
    url: 'input-url',
    lchap: 'input-lchap',
    ochap: 'input-ochap'
};

// Fill input if value exists
function fillFormField(fieldId, value) {
    if (value == null) return; // skip null or undefined
    const input = document.getElementById(fieldId);
    if (input) input.value = value;
}

// Attach click handler to all fetch buttons
function initEpubFetchButtons() {
    document.querySelectorAll('.btn-get-epub-info').forEach(btn => {
        btn.addEventListener('click', () => {
            const epubFile = document.getElementById('input-filepath').value.trim();
            const getParam = btn.dataset.get;
    
            if (!epubFile) {
                showToast("Please enter EPUB filename", "warning");
                return;
            }
    
            fetch(`/get-from-epub?get=${getParam}&epub=${encodeURIComponent(epubFile)}`)
                .then(res => res.json())
                .then(data => {
                    // Fill only the keys returned by the API that exist in fieldMap
                    Object.keys(fieldMap).forEach(key => {
                        if (key in data) fillFormField(fieldMap[key], data[key]);
                    });
                    showToast("✅ Info fetched successfully", "success");
                })
                .catch(err => {
                    console.error(err);
                    showToast("❌ Failed to fetch info", "error");
                });
        });
    });
}

/* --- Scan and import unrecorded EPUBs --- */

async function scanNewFiles() {
  try {
    const resp = await fetch("/scan-unrecorded");
    const j = await resp.json();
    const list = j.files || [];
    const cover_list_len = j.total_unrecorded_covers || 0;
    if (list.length === 0) {
      showToast("No new files found.", "info");
      return;
    }

    const container = document.getElementById("newFilesList");
    const head_info = document.getElementById("span-newfiles-info");
    container.innerHTML = "";
    head_info.innerText = "(" + list.length + ") Cover files found: (" + cover_list_len + ")";
    list.forEach(f => {
      const row = document.createElement("div");
      row.className = "new-file";
      row.innerText = f;
      container.appendChild(row);
    });

    // show modal
    openNewFilesModal();
  } catch (err) {
    showToast("Scan error: " + err, "error");
  }
}

async function importallEPUB() {
  const container = document.getElementById("newFilesList");
  if (!container) return;
  const files = Array.from(container.querySelectorAll(".new-file")).map(d => d.innerText);
  if (files.length === 0) {
    showToast("No files to import.", "info");
    return;
  }

  for (const f of files) {
    try {
      const resp = await fetch("/import-epub", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: f })
      });
      const j = await resp.json();
      if (j.status === "success") {
        showToast(j.message || `${f} imported`, "success");
      } else {
        showToast(j.message || `${f} import failed`, "error");
      }
    } catch (err) {
      showToast("Import error: " + err, "error");
    }
  }

  // reload table and close modal
  dt.ajax.reload();
  closeNewFilesModal();
}

function checkServer() {
    fetch("/status", { cache: "no-store" })
        .then(response => {
            if (!response.ok) throw new Error("Server down");

            document.getElementById("tile_server_stat").innerHTML =
                "<span style='color:green; font-size: small;'>✅ Server is ONLINE</span>";
        })
        .catch(() => {
            document.getElementById("tile_server_stat").innerHTML =
                "<span style='color:red; font-size: small;'>❌ Server is OFFLINE</span>";
        });
};


/* --- Open/close modal --- */


function openAddModal() {
  document.getElementById("addModal").style.display = "flex";
}
function openEditModal() {
  document.getElementById("editModal").style.display = "flex";
}
function openNewFilesModal() {
  document.getElementById("newFilesModal").style.display = "flex";
}
function openSettModal() {
  document.getElementById("settingsModal").style.display = "flex";
}
function openUpdateModal() {
  document.getElementById("updateModal").style.display = "flex";
}

function closeAddModal() {
    document.getElementById("addModal").style.display = "none";
}
function closeEditModal() {
  document.getElementById("editModal").style.display = "none";
}
function closeNewFilesModal() {
  document.getElementById("newFilesModal").style.display = "none";
}
function closeSettModal() {
    document.getElementById("settingsModal").style.display = "none";
}
function closeUpdateModal() {
  document.getElementById("updateModal").style.display = "none";
}


/* --- Simple modal close wiring for existing cancel buttons --- */
document.addEventListener("click", (ev) => {
  if (ev.target.matches(".btn-close-add")) {
    closeAddModal();
  } else if (ev.target.matches(".btn-close-edit")) {
    closeEditModal();
  } else if (ev.target.matches(".btn-close-update")) {
    closeUpdateModal();
  } else if (ev.target.matches(".btn-close-settings")) {
    closeSettModal();
  } else if (ev.target.matches(".btn-close-newfile")) {
    closeNewFilesModal();
  }
});

let hoverBox = null;

function enableHoverPopup() {
    if (!hoverBox) {
        hoverBox = document.createElement("div");
        hoverBox.className = "hover-popup";
        document.body.appendChild(hoverBox);
    }

    // Dynamic binding because table content changes
    $("#table").on("mouseenter", ".novel-hover", function (e) {
        showHoverPopup(e, this);
    });

    $("#table").on("mousemove", ".novel-hover", function (e) {
        moveHoverPopup(e);
    });

    $("#table").on("mouseleave", ".novel-hover", function () {
        hideHoverPopup();
    });
}

function showHoverPopup(e, el) {
    const img = el.dataset.img;
    const author = el.dataset.author;
    const desc = el.dataset.desc;

    hoverBox.innerHTML = `
        ${img ? `<img src="${img}">` : ""}
        <b>${author || "Unknown"}</b><br>
        <div>${desc ? desc.substring(0,200) + "…" : ""}</div>
    `;

    hoverBox.style.display = "block";
    moveHoverPopup(e);
}

function moveHoverPopup(e) {
    hoverBox.style.left = (e.pageX + 15) + "px";
    hoverBox.style.top = (e.pageY + 15) + "px";
}

function hideHoverPopup() {
    hoverBox.style.display = "none";
}

// Check every 5 seconds
setInterval(checkServer, 5000);

