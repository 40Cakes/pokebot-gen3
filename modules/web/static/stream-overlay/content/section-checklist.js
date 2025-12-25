import config from "../config.js";
import {formatInteger, getSectionProgress, getSpeciesCatches} from "../helper.js";

/** @type {HTMLUListElement} */
const ul = document.querySelector("#section-checklist ul");

/** @type {HTMLDivElement} */
const progressBar = document.querySelector("div#section-progress-bar");

/** @type {Object.<string, {li: HTMLLIElement, sprite: PokemonSprite, countSpan: HTMLSpanElement}>} */
const speciesListElements = {};

/**
 * @param {typeof StreamOverlay.SectionChecklist} checklistConfig
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {PokeBotApi.GetMapEncountersResponse} mapEncounters
 * @param {string[]} additionalRouteSpecies
 * @param {EncounterType} encounterType
 */
const updateSectionChecklist = (checklistConfig, stats, mapEncounters, additionalRouteSpecies, encounterType) => {
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

        let completion = getSpeciesCatches(speciesName, checklistConfig, stats);

        const isCompleted = configEntry.goal && completion >= configEntry.goal;
        elements.countSpan.innerText = formatInteger(completion);
        if (isCompleted && !elements.li.classList.contains("completed")) {
            elements.li.classList.add("completed");
        } else if (!isCompleted && elements.li.classList.contains("completed")) {
            elements.li.classList.remove("completed");
        }

        let isAvailableOnThisRoute = false;
        let routeEncounters = mapEncounters.effective.land_encounters;
        if (encounterType === "surfing") {
            routeEncounters = mapEncounters.effective.surf_encounters;
        } else if (encounterType === "fishing_old_rod") {
            routeEncounters = mapEncounters.effective.old_rod_encounters;
        } else if (encounterType === "fishing_good_rod") {
            routeEncounters = mapEncounters.effective.good_rod_encounters;
        } else if (encounterType === "fishing_super_rod") {
            routeEncounters = mapEncounters.effective.super_rod_encounters;
        } else if (encounterType === "rock_smash") {
            routeEncounters = mapEncounters.effective.rock_smash_encounters;
        }

        for (const encounter of routeEncounters) {
            if (encounter.species_name === speciesName || (Array.isArray(configEntry.similarSpecies) && configEntry.similarSpecies.includes(encounter.species_name))) {
                isAvailableOnThisRoute = true;
                break;
            }
        }
        for (const additionalSpeciesName of additionalRouteSpecies) {
            if (additionalSpeciesName === speciesName || (Array.isArray(configEntry.similarSpecies) && configEntry.similarSpecies.includes(additionalSpeciesName))) {
                isAvailableOnThisRoute = true;
                break;
            }
        }

        if (isAvailableOnThisRoute && !isCompleted && !elements.li.classList.contains("in-progress")) {
            elements.li.classList.add("in-progress");
        } else if ((!isAvailableOnThisRoute || isCompleted) && elements.li.classList.contains("in-progress")) {
            elements.li.classList.remove("in-progress");
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
