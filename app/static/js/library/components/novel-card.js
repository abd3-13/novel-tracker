// static/js/library/components/novel-card.js

import { timeAgo } from "./../utils.js";
import { STATUS_STYLE } from "./../config.js"

function renderMeta(icon, value, title = "") {
    if (value === null || value === undefined || value === "" || value === 0 || value === "0" || value === "0/0")
        return "";

    return `
        <div class="nt-meta-item" title="${title}"><i class="ti ti-${icon}"></i><span>${value}</span></div>`;
}

export function renderNovelCard(novel) {

    const unread = novel.reading.unread;
    
    const status = STATUS_STYLE[novel.status] ?? STATUS_STYLE.Reading;

    const percent = novel.chapters.online > 0
        ? Math.round((novel.chapters.local / novel.chapters.online) * 100)
        : 0;
    const cover = novel.cover.url || "cover.webp"
    
    const metaConfig = [
      { enabled: true, icon: "users", value: `${novel.characters.local}/${novel.characters.online}`, title: "Characters" },
      { enabled: true, icon: "percentage", value: novel.reading.percent, title: "Read progress" },
      { enabled: true, icon: "bookmarks", value: novel.reading.chapter, title: `Currently on Ch${novel.reading.chapter}` },
      { enabled: true, icon: "world-www", value: novel.chapters.diff, title: "Not download chapter" },
      { enabled: true, icon: "clock", value: timeAgo(novel.chapters.last_online_update), title: `Updated : ${novel.chapters.last_online_update}`}
    ];
    
    const optionalMeta = metaConfig
      .filter(item => item.enabled)
      .map(item => renderMeta(item.icon, item.value, item.title))
      .join("");
    
    return `
  <div class="col">
    <div class="card bg-transparent border-0 shadow h-100">
      <div class="position-relative">
        <img src="static/img/cover/${cover}" class="card-img-top rounded-1">
        <div class="nt-cover-top-overlay rounded-top-1"></div>
        ${ unread > 0 ? ` <span class="badge bg-red text-white position-absolute top-0 start-0 m-2">+${unread}</span> ` : "" }
        <div class="badge bg-dark-lt position-absolute top-0 end-0 me-1">
          <a class="btn btn-icon btn-sm p-0 ms-1 border-0 bg-transparent" href="${novel.source.url}" role="button">🌐</a>
        </div>
        <div class="position-absolute top-50 end-0 translate-middle-y me-2 d-flex flex-column align-items-end gap-1">${optionalMeta}</div>
        <div class="position-absolute start-0 ms-2" style="bottom: 20px;"><span class="badge ${status.bg} ${status.text}">${novel.status}</span></div>
        <div class="position-absolute bottom-0 start-0 end-0">
          <div class="progress rounded-0 position-relative" style="height: 15px;">
              <div class="progress-bar fw-bold" style="width:${percent}%"></div>
              <span class="position-absolute top-50 start-50 translate-middle fw-bold">${novel.chapters.local}/${novel.chapters.online}</span>
          </div>
        </div>
      </div>
      <div class="card-body p-2">
        <div class="fw-bold text-truncate" data-bs-toggle="tooltip" data-bs-placement="bottom" title="${novel.title}">${novel.title}</div>
        <div class="text-secondary text-truncate text-end small">${novel.author}</div>
      </div>
    </div>
  </div>

    `;
}
