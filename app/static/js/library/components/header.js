// components/header.js
export function renderHeader(library) {
    document.getElementById("library-header").innerHTML = `
      <div class="row align-items-center">
        <div class="col">
          <h2 class="page-title mb-1">Library</h2>
          <div class="text-secondary"><span>${library.stats.total} Novels</span><span class="mx-2">•</span><span>${library.stats.updates} Updates</span><span class="mx-2">•</span><span>${library.stats.missingEpub} Missing EPUB</span></div>
        </div>
        <div class="col-auto">
          <div class="d-flex align-items-center gap-2">
            <button class="btn btn-icon btn-ghost-secondary" title="Settings"><i class="ti ti-settings"></i></button>
            <div class="dropdown">
              <a href="#" class="d-flex align-items-center text-reset text-decoration-none m-0 border-0" data-bs-toggle="dropdown"><i class="avatar avatar-lg ti ti-user"></i></a>
              <div class="dropdown-menu dropdown-menu-end">
                <div class="dropdown-header">Admin</div>
                <a class="dropdown-item" href="#">Profile</a>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item text-danger" href="/logout">Logout</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
}
