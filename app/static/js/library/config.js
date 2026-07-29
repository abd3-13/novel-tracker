export const STATUS_STYLE = {
    Reading: {
        bg: "bg-yellow-lt",
        text: "text-yellow"
    },
    Completed: {
        bg: "bg-green-lt",
        text: "text-green"
    },
    Hiatus: {
        bg: "bg-purple-lt",
        text: "text-purple"
    },
    Dropped: {
        bg: "bg-red-lt",
        text: "text-red"
    },
    Planned: {
        bg: "bg-secondary-lt",
        text: "text-secondary"
    }
};

export const FILTER_FIELDS = [

    {
        category: "Chapters",
        items: [
            {
                field: "unread",
                label: "Unread",
                type: "number",
                editor: "number",
                icon: "book-2",
                getter: novel => novel.reading.unread
            },
            {
                field: "progress",
                label: "Read Progress",
                type: "number",
                editor: "number",
                icon: "progress",
                getter: novel => novel.reading.percent
            },
            {
                field: "local",
                label: "Local Chapters",
                type: "number",
                editor: "number",
                icon: "books",
                getter: novel => novel.chapters.local
            },
            {
                field: "online",
                label: "Online Chapters",
                type: "number",
                editor: "number",
                icon: "books",
                getter: novel => novel.chapters.online
            },
            {
                field: "currentChapter",
                label: "Current Chapter",
                type: "number",
                editor: "number",
                icon: "bookmark",
                getter: novel => novel.reading.chapter
            }
        ]
    },

    {
        category: "Updates",
        items: [
            {
                field: "updates",
                label: "Updates",
                type: "number",
                editor: "number",
                icon: "bell",
                getter: novel => novel.chapters.diff
            },
            {
                field: "lastChapter",
                label: "Last Chapter Time",
                type: "date",
                editor: "date",
                icon: "clock",
                getter: novel => novel.chapters.last_online_update
            }
        ]
    },

    {
        category: "Characters",
        items: [
            {
                field: "localCharacters",
                label: "Local Characters",
                type: "number",
                editor: "number",
                icon: "users",
                getter: novel => novel.characters.local
            },
            {
                field: "onlineCharacters",
                label: "Online Characters",
                type: "number",
                editor: "number",
                icon: "users",
                getter: novel => novel.characters.online
            },
            {
                field: "newCharacters",
                label: "New Characters",
                type: "number",
                editor: "number",
                icon: "users-plus",
                getter: novel => novel.characters.new
            }
        ]
    },

    {
        category: "Novel",
        items: [
            {
                field: "title",
                label: "Title",
                type: "string",
                editor: "text",
                icon: "sort-a-z",
                getter: novel => novel.title
            },
            {
                field: "author",
                label: "Author",
                type: "string",
                editor: "text",
                icon: "user",
                getter: novel => novel.author
            },
            {
                field: "status",
                label: "Status",
                type: "enum",
                editor: "select",
                icon: "circle-check",
                values: [
                    "Reading",
                    "Completed",
                    "Hiatus",
                    "Dropped"
                ],
                getter: novel => novel.status
            },
            {
                field: "tags",
                label: "Tags",
                type: "string",
                editor: "text",
                icon: "tags",
                getter: novel => novel.tags
            },
            {
                field: "source",
                label: "Source",
                type: "string",
                editor: "text",
                icon: "world",
                getter: novel => novel.source.name
            }
        ]
    }

];

export const FILTER_MAP = new Map(
    FILTER_FIELDS
        .flatMap(group => group.items)
        .map(field => [field.field, field])
);

export const OPERATORS = {

    "=": (a, b) => a == b,

    "!=": (a, b) => a != b,

    ">": (a, b) => a > b,

    "<": (a, b) => a < b,

    ">=": (a, b) => a >= b,

    "<=": (a, b) => a <= b,

    "contains": (a, b) =>
        String(a).toLowerCase().includes(String(b).toLowerCase()),

    "not contains": (a, b) =>
        !String(a).toLowerCase().includes(String(b).toLowerCase()),

    "starts with": (a, b) =>
        String(a).toLowerCase().startsWith(String(b).toLowerCase()),

    "ends with": (a, b) =>
        String(a).toLowerCase().endsWith(String(b).toLowerCase())

};

export const TYPE_OPERATORS = {

    string: [
        "=",
        "!=",
        "contains",
        "not contains",
        "starts with",
        "ends with"
    ],

    number: [
        "=",
        "!=",
        ">",
        "<",
        ">=",
        "<="
    ],

    enum: [
        "=",
        "!="
    ],

    date: [
        "=",
        "!=",
        ">",
        "<",
        ">=",
        "<="
    ]

};
