import { getValue } from "./../utils.js"
import { SORT_OPTIONS } from "./../config.js";

export { SORT_OPTIONS };

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
