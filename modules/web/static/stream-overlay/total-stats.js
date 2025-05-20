import {formatInteger, formatRecords, formatShinyAverage} from "./helper.js";
import config from "./config.js";

const totalShinyEncounters = document.querySelector("#total-shiny-encounters-stat");
const totalEncounters = document.querySelector("#total-encounters-stat");
const encounterRate = document.querySelector("#encounter-rate-stat");
const shinyAverage = document.querySelector("#shiny-average-stat");
const totalIVSumRecords = document.querySelector("#total-iv-sum-records-stat");
const phaseRecords = document.querySelector("#phase-records-stat");

/**
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {number} encountersPerHour
 */
function updateTotalStats(stats, encountersPerHour) {
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

export {updateTotalStats};
