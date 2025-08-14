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
    addInfoBubble,
    hideFishingInfoBubble,
    hideInfoBubble,
    resetCustomInfoBubbles,
    updateEncounterInfoBubble,
    updateFishingInfoBubble,
    updateInfoBubbles,
    updatePokeNavInfoBubble
} from "./content/info-bubbles.js";
import {hideCurrentEncounterStats, showCurrentEncounterStats} from "./content/current-encounter-stats.js";
import {updateInputs} from "./content/inputs.js";
import {updateClock} from "./content/clock.js";
import {getLastEncounterSpecies, sleep} from "./helper.js";
import {updateDaycareBox} from "./content/daycare.js";
import {fireConfetti} from "./content/effects.js";

const BATTLE_STATES = ["BATTLE_STARTING", "BATTLE", "BATTLE_ENDING"];

let clockUpdateInterval;
let fetchStatsAfterSummaryScreenTimeout;
let hideEncounterStatsTimeout;

let isInBattle = false;
let isInEggHatch = false;
let isInSummaryScreen = false;
let isInMainMenu = false;
let wasShinyEncounter = false;

/**
 * This fetches all the data the overlay needs for initialisation from the backend.
 *
 * If a fetch fails, it waits for 5 seconds and then tries again until if finally
 * succeeded.
 *
 * @param {OverlayState} state
 * @param {boolean} retryOnError
 * @returns {Promise<void>}
 */
async function doFullUpdate(state, retryOnError = true) {
    let hadSuccess = false;
    while (!hadSuccess) {
        try {
            const customState = await loadAllData(state);

            if (customState["daycare_mode"]) {
                state.daycareMode = true;
            }

            if (customState["countdown_target"]) {
                state.countdownTarget = customState["countdown_target"];
            }

            state.additionalTargetTimers.clear();
            if (customState["species_timers"] && Array.isArray(customState["species_timers"])) {
                for (const speciesName of customState["species_timers"]) {
                    state.additionalTargetTimers.add(speciesName);
                }
            }

            resetCustomInfoBubbles();
            if (customState["info_bubbles"] && Array.isArray(customState["info_bubbles"])) {
                for (const infoBubble of customState["info_bubbles"]) {
                    addInfoBubble(infoBubble);
                }
            }

            isInBattle = BATTLE_STATES.includes(state.gameState);
            isInEggHatch = state.gameState === "EGG_HATCH";
            isInSummaryScreen = state.gameState === "POKEMON_SUMMARY_SCREEN";
            isInMainMenu = state.gameState === "MAIN_MENU" || state.gameState === "TITLE_SCREEN";

            updateMapName(state.map);
            updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
            updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
            updateShinyLog(state.shinyLog);
            updateEncounterLog(state.encounterLog);
            updatePartyList(state.party);
            updateBadgeList(state.emulator.game.title, state.eventFlags);
            updatePhaseStats(state.stats);
            updatePCStorage(state.pokemonStorage, state.party, state.daycare);
            updateTotalStats(state.stats, state.encounterRate);
            updateInfoBubbles(state.mapEncounters, state.stats, state.targetTimers, state.lastEncounterType, state.party, state.countdownTarget);
            updateDaycareBox(state.emulator.bot_mode, state);

            hadSuccess = true;
        } catch (error) {
            if (retryOnError) {
                console.error(error);
                await sleep(5);
            } else {
                throw error;
            }
        }
    }
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
        updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
        updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
        updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
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
        updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
        updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
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

    updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, event.pokemon.species_name_for_stats);
    updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
    updatePhaseStats(state.stats);
    updateTotalStats(state.stats, state.encounterRate);
    updateEncounterInfoBubble(event.pokemon.species_name_for_stats, state.stats, event.pokemon.gender);
    updateInfoBubbles(state.mapEncounters, state.stats, state.targetTimers, event.type, state.party, state.countdownTarget);
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
    updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
    updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
}

/**
 * @param {StreamEvents.PlayerAvatar} event
 * @param {OverlayState} state
 */
function handlePlayerAvatar(event, state) {
    if (state.logPlayerAvatarChange(event)) {
        updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
        updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
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


/**
 * @param {*} event
 * @param {OverlayState} state
 */
function handleCustomEvent(event, state) {
    if (typeof event !== "object" || !event["action"]) {
        return;
    }

    switch (event["action"]) {
        case "show_info_bubble":
            addInfoBubble(event);
            break;

        case "hide_info_bubble":
            hideInfoBubble(event.info_bubble_id);
            break;

        case "reset_custom_info_bubbles":
            resetCustomInfoBubbles();
            break;

        case "add_species_timer":
            state.additionalTargetTimers.add(event.species_name);
            updateInfoBubbles(state.mapEncounters, state.stats, state.targetTimers, state.lastEncounterType, state.party, state.countdownTarget);
            break;

        case "hide_species_timer":
            state.additionalTargetTimers.delete(event.species_name);
            updateInfoBubbles(state.mapEncounters, state.stats, state.targetTimers, state.lastEncounterType, state.party, state.countdownTarget);
            break;

        case "reset_species_timers":
            state.additionalTargetTimers.clear();
            updateInfoBubbles(state.mapEncounters, state.stats, state.targetTimers, state.lastEncounterType, state.party, state.countdownTarget);
            break;

        case "set_countdown":
            state.countdownTarget = event.timestamp;
            updateInfoBubbles(state.mapEncounters, state.stats, state.targetTimers, state.lastEncounterType, state.party, state.countdownTarget);
            break;

        case "enable_daycare_mode":
        case "disable_daycare_mode":
            state.daycareMode = event["action"] === "enable_daycare_mode";
            if (state.daycareMode) {
                fetchers.daycare().then(data => {
                    state.daycare = data;
                    updateDaycareBox(state.emulator.bot_mode, state);
                    updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
                });
            } else {
                updateDaycareBox(state.emulator.bot_mode, state);
                updateRouteEncountersList(state.mapEncounters, state.stats, state.lastEncounterType, config.sectionChecklist, state.emulator.bot_mode, state.daycareMode, state.encounterLog, state.additionalRouteSpecies, getLastEncounterSpecies(state.encounterLog));
                updateSectionChecklist(config.sectionChecklist, state.stats, state.mapEncounters, state.additionalRouteSpecies, state.lastEncounterType);
            }
            break;

        case "confetti":
            let booms = 50;
            if (event["booms"] && Number.isInteger(event["booms"])) {
                booms = event["booms"];
            }

            let durationInSeconds = 10;
            if (event["duration_in_seconds"] && typeof event["duration_in_seconds"] === "number") {
                durationInSeconds = event["duration_in_seconds"];
            }

            fireConfetti(booms, durationInSeconds);
            break;
    }
}


export default async function runOverlay() {
    const state = new OverlayState();
    window.overlayState = state;

    /** @type {EventSource} */
    let eventSource;
    /** @type {{[k: string]: (MessageEvent) => any}} */
    const eventListeners = {};
    let lastStreamedEventTimestamp = new Date().getTime();

    const setUpEventSource = () => {
        try {
            if (eventSource) {
                eventSource.close();
            }
        } catch (error) {
            console.error(error);
        }

        eventSource = getEventSource(eventListeners);
        eventSource.addEventListener("Ping", event => {
            lastStreamedEventTimestamp = new Date().getTime();
        });
        eventSource.addEventListener("error", () => eventSource.close());
        lastStreamedEventTimestamp = new Date().getTime();
    };

    clockUpdateInterval = window.setInterval(() => {
        updateClock(config.startDate, config.timeZone, config.overrideDisplayTimezone);
        if (new Date().getSeconds() === 0) {
            // These things need to be updated once a minute because they might
            // display timers at a minute resolution.
            updateShinyLog(state.shinyLog);
            updatePhaseStats(state.stats);
        }

        // We've had issues with the overlay at some point not receiving any
        // more events from the bot. Since I couldn't figure out what caused
        // this, we'll just try to reconnect if we haven't received anything
        // for more than 15 seconds. (This should never happen organically as
        // button presses alone would reset that counter much more frequently.)
        if (new Date().getSeconds() % 5 === 0) {
            const secondsSinceLastEvent = (new Date().getTime() - lastStreamedEventTimestamp) / 1000;
            if (secondsSinceLastEvent > 15 || eventSource.readyState === EventSource.CLOSED) {
                try {
                    eventSource.close();
                } catch (error) {
                    console.error(error);
                }
                doFullUpdate(state, false)
                    .then(() => setUpEventSource())
                    .catch(error => console.error(error));
            }
        }
    }, 1000);
    updateClock(config.startDate, config.timeZone, config.overrideDisplayTimezone);

    await doFullUpdate(state);

    eventListeners["PerformanceData"] = event => handlePerformanceData(JSON.parse(event.data), state);
    eventListeners["GameState"] = event => handleGameState(JSON.parse(event.data), state);
    eventListeners["BotMode"] = event => handleBotMode(JSON.parse(event.data), state);
    eventListeners["Party"] = event => handleParty(JSON.parse(event.data), state);
    eventListeners["WildEncounter"] = event => handleWildEncounter(JSON.parse(event.data), state);
    eventListeners["MapChange"] = event => handleMapChange(JSON.parse(event.data), state);
    eventListeners["MapEncounters"] = event => handleMapEncounters(JSON.parse(event.data), state);
    eventListeners["PlayerAvatar"] = event => handlePlayerAvatar(JSON.parse(event.data), state);
    eventListeners["PokenavCall"] = event => handlePokenavCall(state);
    eventListeners["FishingAttempt"] = event => handleFishingAttempt(JSON.parse(event.data), state);
    eventListeners["Inputs"] = event => handleInputs(JSON.parse(event.data), state);
    eventListeners["CustomEvent"] = event => handleCustomEvent(JSON.parse(event.data), state);

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
        eventListeners["MapChange"] = event => {
            /** @type {MapLocation} */
            const eventData = JSON.parse(event.data);
            currentLocation.innerText = eventData.map.pretty_name
                .replace("é", "e")
                .replace("’", "'");
        };
    }

    setUpEventSource();

    window.handleCustomEvent = handleCustomEvent;
}
