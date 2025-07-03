import {fetchers, getEventSource, loadAllData} from "./connection.js";
import OverlayState, {WILD_ENCOUNTER_TYPES} from "./state.js";
import {updateMapName, updateRouteEncountersList} from "./content/route-encounters.js";
import config from "./config.js";
import {updateSectionChecklist} from "./content/section-checklist.js";
import {updateShinyLog} from "./content/shiny-log.js";
import {updateEncounterLog} from "./content/encounter-log.js";
import {updatePartyList} from "./content/party-list.js";
import {updateBadgeList} from "./content/badge-list.js";
import {updatePhaseStats} from "./content/phase-stats.js";
import {updatePCStorage, updateTotalStats} from "./content/total-stats.js";
import {
    hideFishingInfoBubble,
    updateEncounterInfoBubble,
    updateFishingInfoBubble,
    updateInfoBubbles,
    updatePokeNavInfoBubble
} from "./content/info-bubbles.js";
import {hideCurrentEncounterStats, showCurrentEncounterStats} from "./content/current-encounter-stats.js";
import {updateInputs} from "./content/inputs.js";
import {updateClock} from "./content/clock.js";
import {getLastEncounterSpecies} from "./helper.js";
import {updateDaycareBox} from "./content/daycare.js";

const BATTLE_STATES = ["BATTLE_STARTING", "BATTLE", "BATTLE_ENDING"];

let clockUpdateInterval;
let fetchStatsAfterSummaryScreenTimeout;
let hideEncounterStatsTimeout;

let isInBattle = false;
let isInEggHatch = false;
let isInSummaryScreen = false;
let isInMainMenu = false;
let wasShinyEncounter = false;

/** @param {OverlayState} state */
async function doFullUpdate(state) {
    await loadAllData(state);

    isInBattle = BATTLE_STATES.includes(state.gameState);
    isInEggHatch = state.gameState === "EGG_HATCH";
    isInSummaryScreen = state.gameState === "POKEMON_SUMMARY_SCREEN";
    isInMainMenu = state.gameState === "MAIN_MENU" || state.gameState === "TITLE_SCREEN";

    updateMapName(state.map);
    updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
    updateSectionChecklist(config.sectionChecklist, state.stats);
    updateShinyLog(state.shinyLog);
    updateEncounterLog(state.encounterLog);
    updatePartyList(state.party);
    updateBadgeList(state.emulator.game.title, state.eventFlags);
    updatePhaseStats(state.stats);
    updatePCStorage(state.pokemonStorage, state.party, state.daycare);
    updateTotalStats(state.stats, state.encounterRate);
    updateInfoBubbles(state.mapEncounters, state.stats, config.targetTimers, state.lastEncounterType, state.party);
    updateDaycareBox(state.emulator.bot_mode, state);
}

/**
 * @param {OverlayState} state
 * @returns {Promise<void>}
 */
async function doUpdateAfterEncounter(state) {
    if (wasShinyEncounter) {
        wasShinyEncounter = false;
        const [stats, shinyLog] = await Promise.all([fetchers.stats(), fetchers.shinyLog()]);
        state.stats = stats;
        state.shinyLog = shinyLog;

        updateShinyLog(state.shinyLog);
        updateSectionChecklist(config.sectionChecklist, state.stats);
        updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
        updatePhaseStats(state.stats);
        updateTotalStats(state.stats, state.encounterRate);
        updatePokeNavInfoBubble(null);
    }
}

/**
 * @param {StreamEvents.PerformanceData} event
 * @param {OverlayState} state
 */
function handlePerformanceData(event, state) {
    state.encounterRate = event.encounter_rate;
    updateTotalStats(state.stats, state.encounterRate);
}

/**
 * @param {StreamEvents.GameState} event
 * @param {OverlayState} state
 */
function handleGameState(event, state) {
    state.gameState = event;

    // We do not update the party list while we are in the egg-hatching
    // animation (to avoid spoilers) so we need to update it once that
    // game mode ended.
    if (isInEggHatch && state.gameState !== "EGG_HATCH") {
        updatePartyList(state.party);
        doUpdateAfterEncounter(state).then(() => {
        });
        isInEggHatch = false;
    } else if (!isInEggHatch && state.gameState === "EGG_HATCH") {
        isInEggHatch = true;
    }

    // If we detect that the game was in the main menu, that means the
    // game has been reset and all data might have changed (due to the
    // save game being reloaded.) So once the game is back in the
    // overworld, we will update _all_ data.
    if (isInMainMenu && state.gameState === "OVERWORLD") {
        doFullUpdate(state);
        isInMainMenu = false;
    } else if (!isInMainMenu && ["TITLE_SCREEN", "MAIN_MENU"].includes(state.gameState)) {
        isInMainMenu = true;
        if (fetchStatsAfterSummaryScreenTimeout) {
            window.clearTimeout(fetchStatsAfterSummaryScreenTimeout);
        }
    }

    // If we enter a Pokémon summary screen, that probably means that we received
    // a new gift Pokémon and should reload the shiny log.
    if (isInSummaryScreen && state.gameState !== "POKEMON_SUMMARY_SCREEN") {
        isInSummaryScreen = false;
    } else if (!isInSummaryScreen && state.gameState === "POKEMON_SUMMARY_SCREEN") {
        isInSummaryScreen = true;
        fetchStatsAfterSummaryScreenTimeout = window.setTimeout(
            () => doUpdateAfterEncounter(state),
            1000);
    }

    // After exiting a battle, we might need to update the shiny log, and also
    // hide the encounter stats again.
    if (isInBattle && state.gameState === "OVERWORLD") {
        hideCurrentEncounterStats();
        doUpdateAfterEncounter(state).then(() => {
        });
        isInBattle = false;
    } else if (!isInBattle && BATTLE_STATES.includes(state.gameState)) {
        isInBattle = true;
    }
}

/**
 * @param {StreamEvents.BotMode} event
 * @param {OverlayState} state
 */
function handleBotMode(event, state) {
    const previousMode = state.emulator.bot_mode;
    state.emulator.bot_mode = event;

    const previousModeWasDaycare = previousMode.toLowerCase().includes("daycare");
    const newModeIsDaycare = event.toLowerCase().includes("daycare");

    if (previousModeWasDaycare !== newModeIsDaycare) {
        updateDaycareBox(event, state);
        updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
    }
}

/**
 * @param {StreamEvents.Party} event
 * @param {OverlayState} state
 */
function handleParty(event, state) {
    state.party = event;
    if (!isInEggHatch) {
        updatePartyList(event);
    }
}

/**
 * @param {StreamEvents.WildEncounter} event
 * @param {OverlayState} state
 */
function handleWildEncounter(event, state) {
    if (hideEncounterStatsTimeout) {
        window.clearTimeout(hideEncounterStatsTimeout);
    }

    state.logEncounter(event);
    if (!WILD_ENCOUNTER_TYPES.includes(event.type)) {
        hideEncounterStatsTimeout = window.setTimeout(() => hideCurrentEncounterStats(), 1000 * config.nonBattleEncounterStatsTimeoutInSeconds);
    }

    if (event.pokemon.is_shiny) {
        wasShinyEncounter = true;
    }

    updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.additionalRouteSpecies, event.pokemon.species_name_for_stats);
    updatePhaseStats(state.stats);
    updateTotalStats(state.stats, state.encounterRate);
    updateEncounterInfoBubble(event.pokemon.species_name_for_stats, state.stats, event.pokemon.gender);
    updateInfoBubbles(state.mapEncounters, state.stats, config.targetTimers, event.type, state.party);
    updateEncounterLog(state.encounterLog);
    showCurrentEncounterStats(event);
}

/**
 * @param {StreamEvents.MapChange} event
 * @param {OverlayState} state
 */
function handleMapChange(event, state) {
    state.logNewMap(event);

    updateMapName(event);
    hideFishingInfoBubble();
    state.additionalRouteSpecies.clear();
    if (state.lastEncounter && ["hatched", "gift", "static"].includes(state.lastEncounter.type)) {
        state.additionalRouteSpecies.add(state.lastEncounter.pokemon.species_name_for_stats);
    }
}

/**
 * @param {StreamEvents.MapEncounters} event
 * @param {OverlayState} state
 */
function handleMapEncounters(event, state) {
    state.mapEncounters = event;
    updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
}

/**
 * @param {StreamEvents.PlayerAvatar} event
 * @param {OverlayState} state
 */
function handlePlayerAvatar(event, state) {
    if (state.logPlayerAvatarChange(event)) {
        updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
    }
}

/**
 * @param {OverlayState} state
 */
function handlePokenavCall(state) {
    state.logPokenavCall()
    updatePokeNavInfoBubble(state.stats);
}

/**
 * @param {StreamEvents.FishingAttempt} event
 * @param {OverlayState} state
 */
function handleFishingAttempt(event, state) {
    state.logFishingAttempt(event);
    updateFishingInfoBubble(state.stats, state.lastFishingRod);
}

/**
 * @param {StreamEvents.Inputs} event
 * @param {OverlayState} state
 */
function handleInputs(event, state) {
    updateInputs(event);
}


export default async function runOverlay() {
    const state = new OverlayState();
    window.overlayState = state;

    clockUpdateInterval = window.setInterval(() => {
        updateClock(config.startDate, config.timeZone, config.overrideDisplayTimezone);
        if (new Date().getSeconds() === 0) {
            // These things need to be updated once a minute because they might
            // display timers at a minute resolution.
            updateShinyLog(state.shinyLog);
            updatePhaseStats(state.stats);
        }
    }, 1000);
    updateClock(config.startDate, config.timeZone, config.overrideDisplayTimezone);

    await doFullUpdate(state);
    const eventSource = getEventSource();

    eventSource.addEventListener("PerformanceData", event => handlePerformanceData(JSON.parse(event.data), state));
    eventSource.addEventListener("GameState", event => handleGameState(JSON.parse(event.data), state));
    eventSource.addEventListener("BotMode", event => handleBotMode(JSON.parse(event.data), state));
    eventSource.addEventListener("Party", event => handleParty(JSON.parse(event.data), state));
    eventSource.addEventListener("WildEncounter", event => handleWildEncounter(JSON.parse(event.data), state));
    eventSource.addEventListener("MapChange", event => handleMapChange(JSON.parse(event.data), state));
    eventSource.addEventListener("MapEncounters", event => handleMapEncounters(JSON.parse(event.data), state));
    eventSource.addEventListener("PlayerAvatar", event => handlePlayerAvatar(JSON.parse(event.data), state));
    eventSource.addEventListener("PokenavCall", event => handlePokenavCall(state));
    eventSource.addEventListener("FishingAttempt", event => handleFishingAttempt(JSON.parse(event.data), state));
    eventSource.addEventListener("Inputs", event => handleInputs(JSON.parse(event.data), state));

    if (config.gymMode) {
        document.getElementById("route-encounters").style.display = "none";
        document.getElementById("daycare-info").style.display = "none";
        document.getElementById("section-checklist").style.display = "none";
        document.getElementById("gym-message").style.display = "block";
        document.getElementById("gym-message").style.flex = "1";

        const gymListEntries = document.querySelectorAll("#gym-message ul li");
        const updateChecklist = () => {
            fetchers.eventFlags().then(flags => {
                for (const li of gymListEntries) {
                    if (flags[li.dataset.flag]) {
                        li.className = "completed";
                    } else {
                        li.className = "";
                    }
                }
            });
        }
        window.setInterval(updateChecklist, 10000);
        updateChecklist();

        const currentLocation = document.querySelector("#gym-message .current-location span");
        currentLocation.innerText = state.map.map.pretty_name
            .replace("é", "e")
            .replace("’", "'");
        eventSource.addEventListener("MapChange", event => {
            /** @type {MapLocation} */
            const eventData = JSON.parse(event.data);
            currentLocation.innerText = eventData.map.pretty_name
                .replace("é", "e")
                .replace("’", "'");
        });
    }
}
