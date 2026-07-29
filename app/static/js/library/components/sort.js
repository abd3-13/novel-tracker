import { getValue } from "./../utils.js"


export const SORT_OPTIONS = [

    {
        group: "Chapters",
        items: [
            { field: "unread", label: "Unread", direction: "desc", icon: "book-2" },
            { field: "progress", label: "Read Progress", direction: "desc", icon: "progress" },
            { field: "online", label: "Online Chapters", direction: "desc", icon: "books" },
            { field: "local", label: "Local Chapters", direction: "desc", icon: "books" }
        ]
    },

    {
        group: "Updates",
        items: [
            { field: "updates", label: "Updates", direction: "desc", icon: "bell" },
            { field: "lastChapter", label: "Last Chapter Time", direction: "desc", icon: "clock" }
        ]
    },

    {
        group: "Characters",
        items: [
            { field: "newCharacters", label: "New Characters", direction: "desc", icon: "users-plus" },
            { field: "characters", label: "Local Characters", direction: "desc", icon: "users" },
            { field: "onlineCharacters", label: "Online Characters", direction: "desc", icon: "cloud" }
        ]
    },

    {
        group: "Novel",
        items: [
            { field: "title", label: "Title", direction: "asc", icon: "sort-a-z" },
            { field: "author", label: "Author", direction: "asc", icon: "user" },
            { field: "source", label: "Source", direction: "asc", icon: "world" },
            { field: "status", label: "Status", direction: "asc", icon: "circle-check" }
        ]
    }

];

export function applySort(library) {

    const { field, direction } = library.sort;

    const multiplier = direction === "asc" ? 1 : -1;

    library.visible.sort((a, b) => {

        const av = getValue(a, field);
        const bv = getValue(b, field);

        if (typeof av === "string")
            return av.localeCompare(bv) * multiplier;

        return (av - bv) * multiplier;

    });

}
