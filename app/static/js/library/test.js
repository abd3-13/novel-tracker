import { getFieldDefinition, getOperators } from "./components/filters.js";
import {  FILTER_FIELDS } from "./config.js";

export function runFilterDefinitionTests() {

    console.group("Filter Definition Tests");

    FILTER_FIELDS.flatMap(g => g.items).forEach(field => {

        console.group(field.label);

        console.log("Definition:", field);
        console.log("Operators:", getOperators(field.id));

        console.groupEnd();

    });

    console.groupEnd();

}
