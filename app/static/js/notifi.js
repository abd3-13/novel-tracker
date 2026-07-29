const typeMap = {
    success: "alert-success",
    error: "alert-danger",
    danger: "alert-danger",
    warning: "alert-warning",
    info: "alert-info",
};

const iconMap = {
    success: "ti-check",
    error: "ti-alert-circle",
    danger: "ti-alert-circle",
    warning: "ti-alert-triangle",
    info: "ti-info-circle",
};

const titleMap = {
    success: "Success",
    error: "Error",
    danger: "Error",
    warning: "Warning",
    info: "Information",
};

function showNotification(message, category = "info", title, delay = 5000) {

    const container = document.getElementById("notification-container");
    if (!container) return;

    const css = typeMap[category] || typeMap.info;
    const icon = iconMap[category] || iconMap.info;
    const heading = title || titleMap[category] || titleMap.info;

    const alert = document.createElement("div");

    alert.className = `alert ${css} alert-dismissible shadow mb-2`;
    alert.setAttribute("role", "alert");

    alert.innerHTML = `
    <div class="d-flex">
       <div class="alert-icon"><i class="icon ti ${icon}"></i></div>
       <div class="flex-fill">
         <h4 class="alert-heading">${heading}</h4>
         <div class="alert-description">${message}</div>
       </div>
       <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    `;

    container.appendChild(alert);

    setTimeout(() => { alert.remove(); }, delay);
}
