export const numberOfEncounterLogEntries = 8;

/**
 * @param {string} speciesName
 * @param {"normal" | "shiny" | "anti-shiny" | "normal-cropped" | "shiny-cropped"} [type]
 * @param {boolean} [animated]
 * @return {string}
 */
export function speciesSpritePath(speciesName, type = "normal", animated = false) {
    speciesName = speciesName
        .replaceAll("♂", "_m")
        .replaceAll("♀", "_f")
        .replaceAll("!", "em")
        .replaceAll("?", "qm")
        .replaceAll(/[^-_.()' a-zA-Z0-9]/g, "_");

    if (animated) {
        return `/static/sprites/pokemon-animated/${type}/${speciesName}.gif`;
    } else {
        return `/static/sprites/pokemon/${type}/${speciesName}.png`;
    }
}

/**
 * @param {boolean} [animated]
 * @return {string}
 */
export function eggSpritePath(animated = false) {
    if (animated) {
        return "/static/sprites/pokemon-animated/Egg.gif";
    } else {
        return "/static/sprites/pokemon/Egg.png";
    }
}

/**
 * @param {string} speciesName
 * @param {"normal" | "shiny" | "anti-shiny" | "normal-cropped" | "shiny-cropped"} [type]
 * @param {boolean} [animated]
 * @return {PokemonSprite}
 */
export function speciesSprite(speciesName, type = "normal", animated = false) {
    const sprite = document.createElement("pokemon-sprite");
    sprite.setAttribute("species", speciesName);
    if (type === "shiny" || type === "shiny-cropped") {
        sprite.setAttribute("shiny", "shiny");
    }
    if (type === "anti-shiny") {
        sprite.setAttribute("shiny", "anti");
    }
    if (type === "shiny-cropped" || type === "normal-cropped") {
        sprite.setAttribute("cropped", "cropped");
    }
    if (animated) {
        sprite.setAttribute("continuously-animated", "continuously-animated");
    }

    return sprite;
}

/**
 * @param {boolean} [animated]
 * @return {PokemonSprite}
 */
export function eggSprite(animated = false) {
    const sprite = document.createElement("pokemon-sprite");
    sprite.setAttribute("species", "Egg");
    if (animated) {
        sprite.setAttribute("continuously-animated", "continuously-animated");
    }
    sprite.classList.add("egg-sprite");

    return sprite;
}

/**
 * @param {"male" | "female" | null} gender
 * @returns {string | HTMLImageElement}
 */
export function genderSprite(gender) {
    let genderSprite = "";
    if (gender === "male") {
        genderSprite = document.createElement("img");
        genderSprite.classList.add("gender-sprite");
        genderSprite.src = "../sprites/other/Male.png";
    } else if (gender === "female") {
        genderSprite = document.createElement("img");
        genderSprite.classList.add("gender-sprite");
        genderSprite.src = "../sprites/other/Female.png";
    }
    return genderSprite;
}

/**
 * @param {Item | null} item
 * @param {HTMLImageElement | null} element
 * @return {string | HTMLImageElement}
 */
export function itemSprite(item, element = null) {
    if (item) {
        const itemSprite = document.createElement("img");
        itemSprite.classList.add("item-sprite");
        itemSprite.src = `../sprites/items/${item.name}.png`;
        itemSprite.alt = item.name;
        return itemSprite;
    } else {
        return "";
    }
}

/**
 * @param {string} name
 * @returns {HTMLImageElement}
 */
export function overlaySprite(name) {
    const sprite = document.createElement("img");
    sprite.classList.add("overlay-sprite");
    sprite.src = `../sprites/stream-overlay/${name}.png`;
    return sprite;
}

/**
 * @param {number} sv
 * @return {HTMLSpanElement}
 */
export function colouredShinyValue(sv) {
    const element = document.createElement("span");
    element.textContent = sv.toLocaleString("en");

    if (sv < 8) {
        element.classList.add("text-yellow");
    } else if (sv > 65527) {
        element.classList.add("text-purple");
    } else {
        element.classList.add("text-red");
    }

    return element;
}

/**
 * @param {number} iv
 * @param {number | null} [natureModifier]
 * @returns {HTMLSpanElement}
 */
export function colouredIV(iv, natureModifier = null) {
    const element = document.createElement("span");
    element.textContent = iv.toLocaleString("en");

    if (iv === 31) {
        element.classList.add("text-yellow");
    } else if (iv >= 26) {
        element.classList.add("text-green");
    } else if (iv > 5) {
        element.classList.add("text-white");
    } else if (iv > 0) {
        element.classList.add("text-red");
    } else {
        element.classList.add("text-purple");
    }

    if (natureModifier && natureModifier > 1) {
        const arrowSprite = overlaySprite("arrow_green");
        arrowSprite.classList.add("arrow-upside-down");
        element.append(arrowSprite)
    } else if (natureModifier && natureModifier < 1) {
        element.append(overlaySprite("arrow_red"));
    }

    return element;
}

/**
 * @param {number} ivSum
 * @returns {HTMLSpanElement}
 */
export function colouredIVSum(ivSum) {
    const element = document.createElement("span");
    element.textContent = ivSum.toLocaleString("en");

    if (ivSum === 186) {
        element.classList.add("text-yellow");
    } else if (ivSum >= 140) {
        element.classList.add("text-green");
    } else if (ivSum > 50) {
        element.classList.add("text-white");
    } else if (ivSum > 0) {
        element.classList.add("text-red");
    } else {
        element.classList.add("text-purple");
    }

    return element;
}

/**
 * @param {EncounterSummary | EncounterTotals} summary
 * @return {string}
 */
export function formatShinyAverage(summary) {
    if (summary.shiny_encounters === null || summary.total_encounters === 0 || summary.shiny_encounters === 0) {
        return "N/A";
    } else {
        return "1/" + Math.round(summary.total_encounters / summary.shiny_encounters).toLocaleString("en");
    }
}

/**
 * @param {SpeciesRecord} max
 * @param {SpeciesRecord} min
 * @return {(string|Node)[]}
 */
export function formatRecords(max, min) {
    const maxSprite = speciesSprite(max.species_name);
    const minSprite = speciesSprite(min.species_name);

    const maxValueLabel = document.createElement("small");
    maxValueLabel.classList.add("text-green");
    maxValueLabel.innerText = max.value.toLocaleString("en");

    const minValueLabel = document.createElement("small");
    minValueLabel.classList.add("text-red");
    minValueLabel.innerText = min.value.toLocaleString("en");

    return [maxSprite, maxValueLabel, " ", minSprite, minValueLabel];
}

/**
 * @param {number} num
 * @returns {string}
 */
export function formatInteger(num) {
    return num.toLocaleString("en");
}

/**
 * @param {number} number
 * @param {number} [precision]
 * @returns {string}
 */
export function shortInteger(number, precision = 3) {
    return Math.abs(Number(number)) >= 1.0e+9
        ? (Math.abs(Number(number)) / 1.0e+9).toFixed(precision) + "B"
        : Math.abs(Number(number)) >= 1.0e+6
            ? (Math.abs(Number(number)) / 1.0e+6).toFixed(precision) + "M"
            : Math.abs(Number(number)).toLocaleString();
}

/**
 * @param {{[k: string]: string | number | Node}} columns
 * @returns {HTMLTableRowElement}
 */
export function renderTableRow(columns) {
    const tr = document.createElement("tr");

    for (const [key, value] of Object.entries(columns)) {
        const td = document.createElement("td");
        td.classList.add(`column-${key}`);

        if (typeof value === "string") {
            td.innerHTML = value;
        } else if (typeof value === "number") {
            td.innerText = value.toString();
        } else if (typeof value === "object" && Array.isArray(value)) {
            for (const part of value) {
                if (typeof part === "object" && part instanceof Node) {
                    td.append(part);
                } else if (typeof part === "string" || typeof part === "number") {
                    td.append(part.toString());
                } else {
                    console.warn(`Unknown data type for an entry in column ${key}: ${typeof part}`);
                }
            }
        } else if (typeof value === "object" && value instanceof Node) {
            td.append(value);
        } else {
            console.warn(`Unknown data type for column ${key}: ${typeof value}`);
        }

        tr.append(td);
    }

    return tr;
}

/**
 * @param {number} columns
 * @returns {HTMLTableRowElement}
 */
export function emptyTableRow(columns) {
    const tr = document.createElement("tr");
    for (let index = 0; index < columns; index++) {
        tr.append(document.createElement("td"));
    }
    return tr;
}

/**
 * @param {string|number} text
 * @returns {HTMLElement}
 */
export function small(text) {
    const element = document.createElement("small");
    element.innerText = text.toString();
    return element;
}

/**
 * @returns {HTMLBRElement}
 */
export function br() {
    return document.createElement("br");
}

/**
 * @param {number} durationInSeconds
 * @returns {Promise<void>}
 */
export async function sleep(durationInSeconds) {
    return new Promise((resolve, reject) => {
        window.setTimeout(() => resolve(), Math.floor(durationInSeconds * 1000));
    });
}

/**
 * @param {number} num
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(num, min, max) {
    return Math.max(min, Math.min(num, max));
}

/**
 * @param {Date|string|number|null} arg
 * @returns {number}
 * @private
 */
function getTimeFromArg(arg) {
    if (arg === null) {
        return new Date().getTime();
    } else if (typeof arg === "string") {
        return new Date(arg).getTime();
    } else if (typeof arg === "object" && arg instanceof Date) {
        return arg.getTime();
    } else {
        return arg;
    }
}

/**
 * @param {number} fromTimestamp
 * @param {number} toTimestamp
 * @returns {string}
 */
export function diffHoursMinutes(fromTimestamp, toTimestamp = null) {
    fromTimestamp = getTimeFromArg(fromTimestamp);
    toTimestamp = getTimeFromArg(toTimestamp);

    const diff = toTimestamp - fromTimestamp;

    const hours = Math.floor(Math.abs(diff) / 3600000);
    const minutes = clamp(Math.floor((Math.abs(diff) % 3600000) / 60000), 0, 59);

    return `${diff < 0 ? "-" : ""}${hours} <small>hr</small> ${minutes} <small>min</small>`;
}

/**
 * @param {Date|string|number} fromTimestamp
 * @param {Date|string|number|null} toTimestamp
 * @param {boolean} [max24Hours] If true, anything longer than 24 hours will be shown in days.
 *                               If false, days are only used at 100+ hours.
 * @returns {string}
 */
export function diffTime(fromTimestamp, toTimestamp = null, max24Hours = false) {
    fromTimestamp = getTimeFromArg(fromTimestamp);
    toTimestamp = getTimeFromArg(toTimestamp);

    const deltaInSeconds = (toTimestamp - fromTimestamp) / 1000;

    let duration = "";
    let durationUnit = "";

    if (deltaInSeconds < 3570) {
        duration = Math.round(deltaInSeconds / 60);
        durationUnit = "min";
    } else if (deltaInSeconds < 36000) {
        duration = (deltaInSeconds / 3600).toLocaleString("en", {maximumFractionDigits: 1});
        durationUnit = "hr";
    } else if (deltaInSeconds < (max24Hours ? 3600 * 24 : 360000)) {
        duration = Math.round(deltaInSeconds / 3600);
        durationUnit = "hr";
    } else if (deltaInSeconds < 864000) {
        duration = (deltaInSeconds / 86400).toLocaleString("en", {maximumFractionDigits: 1});
        durationUnit = "d";
    } else {
        duration = Math.round(deltaInSeconds / 86400);
        durationUnit = "d";
    }

    return `${duration} <small>${durationUnit}</small>`;
}

/**
 * @param {number} encounters
 * @returns {string}
 */
export function calculatePSP(encounters) {
    const binomialDistribution = function (b, a) {
        const c = Math.pow(1 - a, b)
        return 100 * (c * Math.pow(-(1 / (a - 1)), b) - c)
    }

    const chance = binomialDistribution(encounters, 1 / 8192)
    let cumulativeOdds = Math.floor(chance * 100) / 100
    if (cumulativeOdds >= 100 || isNaN(cumulativeOdds)) {
        return "99.99%";
    } else {
        return cumulativeOdds.toLocaleString("en", {maximumSignificantDigits: 3}) + "%";
    }
}

/**
 * @param {string} speciesName
 * @param {StreamOverlay.SectionChecklist} checklistConfig
 * @param {PokeBotApi.GetStatsResponse} stats
 * @return {number}
 */
export function getSpeciesGoal(speciesName, checklistConfig, stats) {
    for (const [checklistSpeciesName, checklistEntry] of Object.entries(checklistConfig)) {
        if (checklistSpeciesName === speciesName || (Array.isArray(checklistEntry.similarSpecies) && checklistEntry.similarSpecies.includes(speciesName))) {
            return checklistEntry.goal;
        }
    }

    return 0;
}

/**
 * @param {string} speciesName
 * @param {StreamOverlay.SectionChecklist} checklistConfig
 * @param {PokeBotApi.GetStatsResponse} stats
 * @return {number}
 */
export function getSpeciesCatches(speciesName, checklistConfig, stats) {
    if (typeof checklistConfig[speciesName] !== "undefined") {
        let result = stats.pokemon[speciesName]?.catches ?? 0;
        for (const similarSpeciesName of checklistConfig[speciesName].similarSpecies) {
            result += stats.pokemon[similarSpeciesName]?.catches ?? 0;
        }
        return result;
    }

    for (const [checklistSpeciesName, checklistEntry] of Object.entries(checklistConfig)) {
        if (Array.isArray(checklistEntry.similarSpecies) && checklistEntry.similarSpecies.includes(speciesName)) {
            let result = stats.pokemon[checklistSpeciesName]?.catches ?? 0;
            for (const similarSpeciesName of checklistEntry.similarSpecies) {
                result += stats.pokemon[similarSpeciesName]?.catches ?? 0;
            }
            return result;
        }
    }

    return 0;
}

/**
 * @param {StreamOverlay.SectionChecklist} sectionChecklist
 * @param {PokeBotApi.GetStatsResponse} stats
 * @return {{caught: number; goal: number}}
 */
export function getSectionProgress(sectionChecklist, stats) {
    let goal = 0;
    let caught = 0;
    for (const [checklistSpeciesName, checklistEntry] of Object.entries(sectionChecklist)) {
        goal += checklistEntry.goal;

        let entryCaught = 0;
        if (stats.pokemon.hasOwnProperty(checklistSpeciesName)) {
            entryCaught += stats.pokemon[checklistSpeciesName].catches;
        }
        if (Array.isArray(checklistEntry.similarSpecies)) {
            for (const similarSpeciesName of checklistEntry.similarSpecies) {
                if (stats.pokemon.hasOwnProperty(similarSpeciesName)) {
                    entryCaught += stats.pokemon[similarSpeciesName].catches;
                }
            }
        }

        caught += clamp(entryCaught, 0, checklistEntry.goal);
    }

    return {caught, goal};
}

/**
 * @param {Encounter[]|null} encounterLog
 * @return {boolean}
 */
export function getLastEncounterSpecies(encounterLog) {
    if (Array.isArray(encounterLog) && encounterLog.length > 0) {
        return encounterLog[0].pokemon.species_name_for_stats;
    } else {
        return null;
    }
}


export function getEmptySpeciesEntry(speciesID, speciesName) {
    return {
        species_id: speciesID,
        species_name: speciesName,
        total_encounters: 0,
        shiny_encounters: 0,
        catches: 0,
        total_highest_iv_sum: null,
        total_lowest_iv_sum: null,
        total_highest_sv: null,
        total_lowest_sv: null,
        phase_encounters: 0,
        phase_highest_iv_sum: null,
        phase_lowest_iv_sum: null,
        phase_highest_sv: null,
        phase_lowest_sv: null,
        last_encounter_time: null,
    }
}
