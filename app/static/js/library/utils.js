export function timeAgo(dateString) {
    if (!dateString || dateString === "0") return "";

    const now = new Date();
    const date = new Date(dateString);

    let diff = Math.floor((now - date) / 1000);

    const units = [
        { label: "y",  secs: 31536000 },
        { label: "mo", secs: 2592000 },
        { label: "w",  secs: 604800 },
        { label: "d",  secs: 86400 },
        { label: "h",  secs: 3600 },
        { label: "m",  secs: 60 },
        { label: "s",  secs: 1 }
    ];

    for (const unit of units) {
        const value = Math.floor(diff / unit.secs);
        if (value >= 1)
            return `${value}${unit.label}`;
    }

    return "now";
}

export function applySearch(library) {

    const search = library.search.trim().toLowerCase();

    if (!search)
        return;

    library.visible = library.visible.filter(novel => {

        return [

            novel.title,
            novel.author,
            novel.description,
            novel.tags,
            novel.notes

        ].some(value =>
            String(value || "")
                .toLowerCase()
                .includes(search)
        );

    });

}


export function getValue(novel, field) {

    switch (field) {

        case "title":
            return novel.title;

        case "author":
            return novel.author;

        case "unread":
            return novel.reading.unread;

        case "updates":
            return novel.chapters.diff;

        case "local":
            return novel.chapters.local;

        case "online":
            return novel.chapters.online;

        case "characters":
            return novel.characters.local;

        case "onlineCharacters":
            return novel.characters.online;

        case "newCharacters":
            return novel.characters.new;

        case "progress":
            return novel.reading.percent;

        case "lastChapter":
            return novel.chapters.last_online_update;

        case "source":
            return novel.source.name;

        case "status":
            return novel.status;

        default:
            return "";
    }

}

let filterId = 0;

export function nextFilterId() {
    return ++filterId;
}
