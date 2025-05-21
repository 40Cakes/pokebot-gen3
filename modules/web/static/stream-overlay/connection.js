import {updateMapName, updateRouteEncountersList, updateSpeciesChecklist} from "./species-list.js";
import {updateShinyLog} from "./shiny-list.js";
import {updateEncounterLog} from "./encounter-list.js";
import config from "./config.js";
import {updatePartyList} from "./party-list.js";
import {updateBadgeList} from "./badge-list.js";
import {updateSectionProgressBar} from "./section-progress-bar.js";
import {updatePhaseStats} from "./phase-stats.js";
import {updateTotalStats} from "./total-stats.js";
import {updateInputs} from "./inputs.js";
import {updateClock} from "./clock.js";
import {
    hideFishingInfoBubble,
    updateEncounterInfoBubble,
    updateFishingInfoBubble,
    updateInfoBubbles,
    updatePokeNavInfoBubble
} from "./info-bubbles.js";
import {hideEncounterStats, showEncounterStats} from "./encounter-stats.js";
import {numberOfEncounterLogEntries} from "./helper.js";

let interval;
let hideEncounterStatsTimeout;

export default function initOverlay() {
    if (interval) {
        window.clearInterval(interval);
    }
    interval = window.setInterval(() => updateClock(config.startDate, config.timeZone, config.overrideDisplayTimezone), 1000);
    updateClock(config.startDate, config.timeZone, config.overrideDisplayTimezone);

    const initialFetch = [
        fetch("/stats").then(response => response.json()),
        fetch("/map").then(response => response.json()),
        fetch("/map_encounters").then(response => response.json()),
        fetch("/shiny_log").then(response => response.json()),
        fetch("/encounter_log").then(response => response.json()),
        fetch("/player_avatar").then(response => response.json()),
        fetch("/party").then(response => response.json()),
        fetch("/emulator").then(response => response.json()),
        fetch("/event_flags").then(response => response.json()),
        fetch("/encounter_rate").then(response => response.json()),
        fetch("/game_state").then(response => response.json()),
    ];

    Promise.all(initialFetch).then(
        /**
         * @param {[
         *     PokeBotApi.GetStatsResponse,
         *     PokeBotApi.GetMapResponse,
         *     PokeBotApi.GetMapEncountersResponse,
         *     PokeBotApi.GetShinyLogResponse,
         *     PokeBotApi.GetEncounterLogResponse,
         *     PokeBotApi.GetPlayerAvatarResponse,
         *     PokeBotApi.GetPartyResponse,
         *     PokeBotApi.GetEmulatorResponse,
         *     PokeBotApi.GetEventFlagsResponse,
         *     PokeBotApi.GetEncounterRateResponse,
         *     PokeBotApi.GetGameStateResponse,
         * ]} data
         */
        ([stats, map, mapEncounters, shinyLog, encounterLog, playerAvatar, party, emulator, eventFlags, encounterRate, gameState]) => {
            const wildEncounterTypes = ["land", "surfing", "fishing_old_rod", "fishing_good_rod", "fishing_super_rod", "rock_smash"];
            /** @type {EncounterType} lastEncounterType */
            let lastEncounterType = "land";
            /** @type {Encounter} */
            let lastEncounter = encounterLog.length > 0 ? encounterLog[0] : null;
            let additionalRouteSpecies = [];
            if (encounterLog.length > 0 && wildEncounterTypes.includes(encounterLog[0].type)) {
                lastEncounterType = encounterLog[0].type;
            } else if (encounterLog.length > 0 && ["hatched", "gift", "static"].includes(encounterLog[0].type)) {
                additionalRouteSpecies.push(encounterLog[0].pokemon.species.name);
            }
            if (lastEncounterType === "land" && playerAvatar.flags.Surfing) {
                lastEncounterType = "surfing";
            } else if (lastEncounterType === "surfing" && !playerAvatar.flags.Surfing) {
                lastEncounterType = "land";
            }

            updateMapName(map);
            updateRouteEncountersList(mapEncounters, stats, lastEncounterType, config.speciesChecklist, additionalRouteSpecies);
            updateSpeciesChecklist(config.speciesChecklist, stats);
            updateShinyLog(shinyLog);
            updateEncounterLog(encounterLog);
            updatePartyList(party);
            updateBadgeList(emulator.game.title, eventFlags);
            updateSectionProgressBar(config.speciesChecklist, stats);
            updatePhaseStats(stats);
            updateTotalStats(stats, encounterRate.encounter_rate);
            updateInfoBubbles(mapEncounters, stats, config.targetTimers, lastEncounterType, party);

            const battleStates = ["BATTLE_STARTING", "BATTLE", "BATTLE_ENDING"];
            let isInBattle = battleStates.includes(gameState);
            let isInEggHatch = gameState === "EGG_HATCH";
            let wasShinyEncounter = false;

            /** @param {StreamEvents.PerformanceData} data */
            const handlePerformanceData = data => {
                encounterRate = data;
                updateTotalStats(stats, encounterRate.encounter_rate);
            };

            /** @param {StreamEvents.GameState} gameState */
            const handleGameState = gameState => {
                console.warn(gameState);
                if (isInEggHatch && gameState !== "EGG_HATCH") {
                    updatePartyList(party);
                    isInEggHatch = false;
                } else if (!isInEggHatch && gameState === "EGG_HATCH") {
                    isInEggHatch = true;
                }
                if (isInBattle && gameState === "OVERWORLD") {
                    hideEncounterStats();
                    if (wasShinyEncounter) {
                        wasShinyEncounter = false;
                        Promise.all([
                            fetch("/stats").then(response => response.json()),
                            fetch("/shiny_log").then(response => response.json()),
                        ]).then(
                            /**
                             * @param {PokeBotApi.GetStatsResponse} newStats
                             * @param {PokeBotApi.GetShinyLogResponse} newShinyLog
                             */
                            ([newStats, newShinyLog]) => {
                                stats = newStats;
                                shinyLog = newShinyLog;

                                updateShinyLog(shinyLog);
                                updateSpeciesChecklist(config.speciesChecklist, stats);
                                updateSectionProgressBar(config.speciesChecklist, stats);
                                updateRouteEncountersList(mapEncounters, stats, lastEncounterType, config.speciesChecklist, additionalRouteSpecies);
                                updatePhaseStats(stats);
                                updateTotalStats(stats);
                            });
                    }
                    isInBattle = false;
                }

                if (!isInBattle && battleStates.includes(gameState)) {
                    isInBattle = true;
                }
            };

            /** @param {StreamEvents.Party} data */
            const handleParty = data => {
                party = data;
                if (!isInEggHatch) {
                    updatePartyList(data);
                }
            };

            /** @param {StreamEvents.PlayerAvatar} data */
            const handlePlayerAvatar = data => {
                console.log(data);
                playerAvatar = data;
                if (lastEncounterType === "land" && playerAvatar.flags.Surfing) {
                    lastEncounterType = "surfing";
                    updateRouteEncountersList(mapEncounters, stats, lastEncounterType, config.speciesChecklist, additionalRouteSpecies);
                } else if (lastEncounterType === "surfing" && !playerAvatar.flags.Surfing) {
                    lastEncounterType = "land";
                    updateRouteEncountersList(mapEncounters, stats, lastEncounterType, config.speciesChecklist, additionalRouteSpecies);
                }
            };

            /** @param {StreamEvents.MapChange} data */
            const handleMap = data => {
                updateMapName(data);
                hideFishingInfoBubble();
                additionalRouteSpecies = [];
                if (lastEncounter && ["hatched", "gift", "static"].includes(lastEncounter.type) && !additionalRouteSpecies.includes(lastEncounter.pokemon.species.name)) {
                    additionalRouteSpecies.push(lastEncounter.pokemon.species.name);
                }
            };

            /** @param {StreamEvents.MapEncounters} data */
            const handleMapEncounters = data => {
                mapEncounters = data;
                updateRouteEncountersList(mapEncounters, stats, lastEncounterType, config.speciesChecklist, additionalRouteSpecies);
            };

            const handlePokenavCall = () => {
                if (stats.current_phase) {
                    stats.current_phase.pokenav_calls++;
                    updatePokeNavInfoBubble(stats);
                }
            };

            /** @param {StreamEvents.FishingAttempt} attempt */
            const handleFishingAttempt = attempt => {
                console.warn(attempt);
                if (stats.current_phase) {
                    stats.current_phase.fishing_attempts++;
                    if (attempt.result === "Encounter") {
                        stats.current_phase.successful_fishing_attempts++;
                        stats.current_phase.current_unsuccessful_fishing_streak = 0;
                    } else {
                        stats.current_phase.current_unsuccessful_fishing_streak++;
                        if (stats.current_phase.longest_unsuccessful_fishing_streak < stats.current_phase.current_unsuccessful_fishing_streak) {
                            stats.current_phase.longest_unsuccessful_fishing_streak = stats.current_phase.current_unsuccessful_fishing_streak
                        }
                    }
                    let rod = "Old";
                    if (attempt.rod === "GoodRod") {
                        rod = "Good";
                    } else if (attempt.rod === "SuperRod") {
                        rod = "Super";
                    }
                    updateFishingInfoBubble(stats, rod);
                }
            };

            /** @param {StreamEvents.Inputs} inputs */
            const handleInput = inputs => {
                updateInputs(inputs);
            };

            /** @param {StreamEvents.WildEncounter} encounter */
            const handleWildEncounter = encounter => {
                if (hideEncounterStatsTimeout) {
                    window.clearTimeout(hideEncounterStatsTimeout);
                }

                lastEncounter = encounter;
                if (wildEncounterTypes.includes(encounter.type)) {
                    lastEncounterType = encounter.type;
                } else {
                    hideEncounterStatsTimeout = window.setTimeout(() => hideEncounterStats(), 1000 * config.nonBattleEncounterStatsTimeoutInSeconds);
                }

                if (["hatched", "gift", "static"].includes(encounter.type) && !additionalRouteSpecies.includes(encounter.pokemon.species.name)) {
                    additionalRouteSpecies.push(encounter.pokemon.species.name);
                }

                encounterLog.unshift(encounter);
                while (encounterLog.length > numberOfEncounterLogEntries) {
                    encounterLog.pop();
                }

                stats.totals.total_encounters++;

                const sv = encounter.pokemon.shiny_value;
                const ivSum =
                    encounter.pokemon.ivs.hp +
                    encounter.pokemon.ivs.attack +
                    encounter.pokemon.ivs.defence +
                    encounter.pokemon.ivs.special_attack +
                    encounter.pokemon.ivs.special_defence +
                    encounter.pokemon.ivs.speed;

                if (!stats.totals.total_highest_iv_sum?.species_name || stats.totals.total_highest_iv_sum.value < ivSum) {
                    stats.totals.total_highest_iv_sum = {
                        species_name: encounter.pokemon.species.name,
                        value: ivSum,
                    };
                }

                if (!stats.totals.total_lowest_iv_sum?.species_name || stats.totals.total_lowest_iv_sum.value > ivSum) {
                    stats.totals.total_lowest_iv_sum = {
                        species_name: encounter.pokemon.species.name,
                        value: ivSum,
                    };
                }

                if (!stats.totals.total_highest_sv?.species_name || stats.totals.total_highest_sv.value < sv) {
                    stats.totals.total_highest_sv = {
                        species_name: encounter.pokemon.species.name,
                        value: sv,
                    };
                }

                if (!stats.totals.total_lowest_sv?.species_name || stats.totals.total_lowest_sv.value > sv) {
                    stats.totals.total_lowest_sv = {
                        species_name: encounter.pokemon.species.name,
                        value: sv,
                    };
                }

                stats.totals.phase_encounters++;

                if (!stats.totals?.phase_highest_iv_sum?.species_name || stats.totals.phase_highest_iv_sum.value < ivSum) {
                    stats.totals.phase_highest_iv_sum = {
                        species_name: encounter.pokemon.species.name,
                        value: ivSum,
                    };
                }

                if (!stats.totals.phase_lowest_iv_sum?.species_name || stats.totals.phase_lowest_iv_sum.value > ivSum) {
                    stats.totals.phase_lowest_iv_sum = {
                        species_name: encounter.pokemon.species.name,
                        value: ivSum,
                    };
                }

                if (!stats.totals.phase_highest_sv?.species_name || stats.totals.phase_highest_sv.value < sv) {
                    stats.totals.phase_highest_sv = {
                        species_name: encounter.pokemon.species.name,
                        value: sv,
                    };
                }

                if (!stats.totals.phase_lowest_sv?.species_name || stats.totals.phase_lowest_sv.value > sv) {
                    stats.totals.phase_lowest_sv = {
                        species_name: encounter.pokemon.species.name,
                        value: sv,
                    };
                }

                if (!stats.pokemon.hasOwnProperty(encounter.pokemon.species.name)) {
                    stats.pokemon[encounter.pokemon.species.name] = {
                        species_id: encounter.pokemon.species.index,
                        species_name: encounter.pokemon.species.name,
                        total_encounters: 1,
                        shiny_encounters: encounter.pokemon.is_shiny ? 1 : 0,
                        catches: 0,
                        total_highest_iv_sum: ivSum,
                        total_lowest_iv_sum: ivSum,
                        total_highest_sv: sv,
                        total_lowest_sv: sv,
                        phase_encounters: 1,
                        phase_highest_iv_sum: ivSum,
                        phase_lowest_iv_sum: ivSum,
                        phase_highest_sv: sv,
                        phase_lowest_sv: sv,
                        last_encounter_time: new Date().toISOString(),
                    };
                } else {
                    stats.pokemon[encounter.pokemon.species.name].total_encounters++;
                    stats.pokemon[encounter.pokemon.species.name].phase_encounters++;
                    stats.pokemon[encounter.pokemon.species.name].last_encounter_time = new Date().toISOString();
                    if (stats.pokemon[encounter.pokemon.species.name].total_highest_iv_sum < ivSum) {
                        stats.pokemon[encounter.pokemon.species.name].total_highest_iv_sum = ivSum;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].total_lowest_iv_sum > ivSum) {
                        stats.pokemon[encounter.pokemon.species.name].total_lowest_iv_sum = ivSum;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].total_highest_sv < sv) {
                        stats.pokemon[encounter.pokemon.species.name].total_highest_sv = sv;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].total_lowest_sv > sv) {
                        stats.pokemon[encounter.pokemon.species.name].total_lowest_sv = sv;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].phase_highest_iv_sum < ivSum) {
                        stats.pokemon[encounter.pokemon.species.name].phase_highest_iv_sum = ivSum;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].phase_lowest_iv_sum > ivSum) {
                        stats.pokemon[encounter.pokemon.species.name].phase_lowest_iv_sum = ivSum;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].phase_highest_sv < sv) {
                        stats.pokemon[encounter.pokemon.species.name].phase_highest_sv = sv;
                    }
                    if (stats.pokemon[encounter.pokemon.species.name].phase_lowest_sv > sv) {
                        stats.pokemon[encounter.pokemon.species.name].phase_lowest_sv = sv;
                    }
                }

                stats.current_phase.encounters++;
                if (!stats.current_phase.highest_iv_sum?.species_name || stats.current_phase.highest_iv_sum.value < ivSum) {
                    stats.current_phase.highest_iv_sum = {
                        species_name: encounter.pokemon.species.name,
                        value: ivSum,
                    };
                }
                if (!stats.current_phase.lowest_iv_sum?.species_name || stats.current_phase.lowest_iv_sum.value > ivSum) {
                    stats.current_phase.lowest_iv_sum = {
                        species_name: encounter.pokemon.species.name,
                        value: ivSum,
                    };
                }
                if (!stats.current_phase.highest_sv?.species_name || stats.current_phase.highest_sv.value < sv) {
                    stats.current_phase.highest_sv = {
                        species_name: encounter.pokemon.species.name,
                        value: sv,
                    };
                }
                if (!stats.current_phase.lowest_sv?.species_name || stats.current_phase.lowest_sv.value > sv) {
                    stats.current_phase.lowest_sv = {
                        species_name: encounter.pokemon.species.name,
                        value: sv,
                    };
                }
                if (stats.current_phase?.current_streak?.species_name === encounter.pokemon.species.name) {
                    stats.current_phase.current_streak.value++;
                } else {
                    stats.current_phase.current_streak = {
                        species_name: encounter.pokemon.species.name,
                        value: 1,
                    };
                }
                if (!stats.current_phase?.longest_streak?.species_name || stats.current_phase.longest_streak.value < stats.current_phase.current_streak.value) {
                    stats.current_phase.longest_streak = {
                        species_name: stats.current_phase.current_streak.species_name,
                        value: stats.current_phase.current_streak.value,
                    };
                }

                if (encounter.pokemon.is_shiny) {
                    wasShinyEncounter = true;
                    stats.totals.shiny_encounters++;
                    stats.pokemon[encounter.pokemon.species.name].shiny_encounters++;
                    updatePokeNavInfoBubble(null);
                }

                updateRouteEncountersList(mapEncounters, stats, lastEncounterType, config.speciesChecklist, additionalRouteSpecies, encounter.pokemon.species.name);
                updatePhaseStats(stats);
                updateTotalStats(stats, encounterRate.encounter_rate);
                updateEncounterInfoBubble(encounter.pokemon.species.name, stats);
                updateInfoBubbles(mapEncounters, stats, config.targetTimers, encounter.type, party);
                updateEncounterLog(encounterLog);
                showEncounterStats(encounter);
            };

            const url = new URL(window.location.origin + "/stream_events");
            url.searchParams.append("topic", "PerformanceData");
            url.searchParams.append("topic", "BotMode");
            url.searchParams.append("topic", "GameState");
            url.searchParams.append("topic", "Party");
            url.searchParams.append("topic", "WildEncounter");
            url.searchParams.append("topic", "Map");
            url.searchParams.append("topic", "MapEncounters");
            url.searchParams.append("topic", "Player");
            url.searchParams.append("topic", "PlayerAvatar");
            url.searchParams.append("topic", "Inputs");
            url.searchParams.append("topic", "PokenavCall");
            url.searchParams.append("topic", "FishingAttempt");

            const eventSource = new EventSource(url);
            eventSource.addEventListener("PerformanceData", event => handlePerformanceData(JSON.parse(event.data)));
            eventSource.addEventListener("GameState", event => handleGameState(JSON.parse(event.data)));
            eventSource.addEventListener("Party", event => handleParty(JSON.parse(event.data)));
            eventSource.addEventListener("WildEncounter", event => handleWildEncounter(JSON.parse(event.data)));
            eventSource.addEventListener("MapChange", event => handleMap(JSON.parse(event.data)));
            eventSource.addEventListener("MapEncounters", event => handleMapEncounters(JSON.parse(event.data)));
            eventSource.addEventListener("PlayerAvatar", event => handlePlayerAvatar(JSON.parse(event.data)));
            eventSource.addEventListener("PokenavCall", event => handlePokenavCall());
            eventSource.addEventListener("FishingAttempt", event => handleFishingAttempt(JSON.parse(event.data)));
            // eventSource.addEventListener("Player", event => handlePlayer(JSON.parse(event.data)));
            eventSource.addEventListener("Inputs", event => handleInput(JSON.parse(event.data)));
        });
};
