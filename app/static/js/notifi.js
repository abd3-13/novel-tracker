import { escapeHtml } from './library/utils.js';

const typeMap = {
  success: 'alert-success',
  error: 'alert-danger',
  danger: 'alert-danger',
  warning: 'alert-warning',
  info: 'alert-info'
};

const iconMap = {
  success: 'ti-check',
  error: 'ti-alert-circle',
  danger: 'ti-alert-circle',
  warning: 'ti-alert-triangle',
  info: 'ti-info-circle'
};

const titleMap = {
  success: 'Success',
  error: 'Error',
  danger: 'Error',
  warning: 'Warning',
  info: 'Information'
};

const delayMap = { success: 3, error: 10, danger: 10, warning: 5, info: 4 };

export function showNotification(message, category = 'info', title, delay) {
  const container = document.getElementById('notification-container');
  if (!container) return;

  const css = typeMap[category] || typeMap.info;
  const icon = iconMap[category] || iconMap.info;
  const heading = title || titleMap[category] || titleMap.info;
  // Use category-specific delay when delay isn't explicitly provided const
  const delaySec = (delay ?? delayMap[category] ?? delayMap.info) * 1000;

  const alert = document.createElement('div');

  alert.className = `alert ${css} alert-dismissible mb-2`;
  alert.setAttribute('role', 'alert');

  alert.innerHTML = `
    <div class="alert-icon"><i class="icon ti ${icon}"></i></div>
       <div>
         <h4 class="alert-heading">${escapeHtml(heading)}</h4>
         <div class="alert-description">${escapeHtml(message)}</div>
       </div>
       <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  container.appendChild(alert);

  setTimeout(() => {
    alert.remove();
  }, delaySec);
}
