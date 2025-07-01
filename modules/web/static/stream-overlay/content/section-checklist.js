import config from "../config.js";
import {formatInteger, getSectionProgress} from "../helper.js";

/** @type {HTMLUListElement} */
const ul = document.querySelector("#section-checklist ul");

/** @type {HTMLDivElement} */
const progressBar = document.querySelector("div#section-progress-bar");

/** @type {Object.<string, {li: HTMLLIElement, sprite: PokemonSprite, countSpan: HTMLSpanElement}>} */
const speciesListElements = {};

/**
 * @param {typeof StreamOverlay.SectionChecklist} checklistConfig
 * @param {PokeBotApi.GetStatsResponse} stats
 */
const updateSectionChecklist = (checklistConfig, stats) => {
    // Special case for then the checklist is empty or undefined.
    if (!checklistConfig || Object.keys(checklistConfig).length === 0) {
        ul.parentElement.style.display = "none";
        ul.innerHTML = "";
        return;
    }

    // This is run the first time the list gets updated and will create all the entries.
    if (ul.childElementCount === 0) {
        for (const speciesName in checklistConfig) {
            const entry = checklistConfig[speciesName];
            if (entry.hidden) {
                continue;
            }

            const elements = {
                li: document.createElement("li"),
                sprite: document.createElement("pokemon-sprite"),
                countSpan: document.createElement("span"),
            };

            elements.sprite.setAttribute("species", speciesName);
            elements.sprite.setAttribute("cropped", "cropped");
            elements.sprite.setAttribute("shiny", "shiny");

            const span = document.createElement("span");
            span.append(elements.countSpan);
            if (entry.goal) {
                const goalSmall = document.createElement("small");
                goalSmall.innerText = `/${entry.goal}`;
                span.append(goalSmall);
            }

            const tick = document.createElement("img");
            tick.src = "/static/sprites/stream-overlay/tick.png";
            tick.classList.add("tick");
            span.append(tick);

            elements.li.append(elements.sprite, span);
            ul.append(elements.li);
            speciesListElements[speciesName] = elements;
        }
    }

    // Updates the data inside the entries.
    for (const speciesName in checklistConfig) {
        const configEntry = checklistConfig[speciesName];
        const elements = speciesListElements[speciesName];

        let completion = 0;
        if (stats.pokemon.hasOwnProperty(speciesName)) {
            completion += stats.pokemon[speciesName].catches;
        }
        if (Array.isArray(configEntry.similarSpecies)) {
            for (const similarSpecies of configEntry.similarSpecies) {
                if (stats.pokemon.hasOwnProperty(similarSpecies)) {
                    completion += stats.pokemon[similarSpecies].catches;
                }
            }
        }

        elements.countSpan.innerText = formatInteger(completion);
        if (configEntry.goal && completion >= configEntry.goal && !elements.li.classList.contains("completed")) {
            elements.li.classList.add("completed");
        } else if ((!configEntry.goal || completion < configEntry.goal) && elements.li.classList.contains("completed")) {
            elements.li.classList.remove("completed");
        }

        // Updates the progress bar.
        const {goal, caught} = getSectionProgress(config.sectionChecklist, stats);
        const percentage = goal > 0 ? Math.round(100 * caught / goal) : 0;

        /** @type {HTMLDivElement} */
        const filled = progressBar.children[0];
        filled.style.width = `${percentage}%`;

        if (percentage === 100) {
            filled.classList.remove("yellow");
            filled.classList.add("green");
        } else {
            filled.classList.remove("green");
            filled.classList.add("yellow");
        }
    }
};

export {updateSectionChecklist};
