import {formatInteger, formatRecords, formatShinyAverage, getSectionProgress} from "../helper.js";
import config from "../config.js";

const shinyDexProgress = document.querySelector("#shiny-dex-progress-stat");
const totalShinyEncounters = document.querySelector("#total-shiny-encounters-stat");
const totalEncounters = document.querySelector("#total-encounters-stat");
const encounterRate = document.querySelector("#encounter-rate-stat");
const shinyAverage = document.querySelector("#shiny-average-stat");
const totalIVSumRecords = document.querySelector("#total-iv-sum-records-stat");
const phaseRecords = document.querySelector("#phase-records-stat");

let shiniesFromBeforeThisSection = 0;

/**
 * @param {PokemonStorage} storage
 * @param {Pokemon[]} party
 * @param {PokeBotApi.GetDaycareResponse} daycare
 */
function updatePCStorage(storage, party, daycare) {
    const ignoreSpecies = new Set();
    for (const speciesName in config.sectionChecklist) {
        ignoreSpecies.add(speciesName);
        if (Array.isArray(config.sectionChecklist[speciesName].similarSpecies)) {
            for (const similarSpecies of config.sectionChecklist[speciesName].similarSpecies) {
                ignoreSpecies.add(similarSpecies);
            }
        }
    }

    const species = new Set();
    for (const box of storage.boxes) {
        for (const slot of box.slots) {
            if (slot.pokemon.is_shiny && !ignoreSpecies.has(slot.pokemon.species.name)) {
                species.add(slot.pokemon.species.name);
            }
        }
    }

    for (const pokemon of party) {
        if (pokemon.is_shiny && !ignoreSpecies.has(pokemon.species.name)) {
            species.add(pokemon.species.name);
        }
    }

    if (daycare.pokemon1 && daycare.pokemon1.is_shiny && !ignoreSpecies.has(daycare.pokemon1.species.name)) {
        species.add(daycare.pokemon1.species.name);
    }

    if (daycare.pokemon2 && daycare.pokemon2.is_shiny && !ignoreSpecies.has(daycare.pokemon2.species.name)) {
        species.add(daycare.pokemon2.species.name);
    }

    shiniesFromBeforeThisSection = species.size;
}

/**
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {number} encountersPerHour
 */
function updateTotalStats(stats, encountersPerHour) {
    let uniqueShiniesCaught = shiniesFromBeforeThisSection + getSectionProgress(config.sectionChecklist, stats).caught

    shinyDexProgress.innerText = `${formatInteger(uniqueShiniesCaught)}/${formatInteger(config.totalShinySpeciesTarget)}`;
    totalShinyEncounters.innerText = formatInteger(stats.totals.shiny_encounters);
    totalEncounters.innerText = formatInteger(stats.totals.total_encounters);
    encounterRate.innerHTML = formatInteger(encountersPerHour) + "<small>/hr</small>";
    shinyAverage.innerHTML = formatShinyAverage(stats.totals);

    totalIVSumRecords.innerHTML = "";
    if (stats.totals.total_highest_iv_sum?.species_name && stats.totals.total_lowest_iv_sum?.species_name) {
        totalIVSumRecords.append(...formatRecords(stats.totals.total_highest_iv_sum, stats.totals.total_lowest_iv_sum));
    }

    phaseRecords.innerHTML = "";
    const longestPhase = config?.overrideLongestPhase ?? stats.longest_phase;
    const shortestPhase = config?.overrideShortestPhase ?? stats.shortest_phase;
    if (longestPhase?.species_name && shortestPhase?.species_name) {
        phaseRecords.append(...formatRecords(shortestPhase, longestPhase));
    }
}

export {updatePCStorage, updateTotalStats};
