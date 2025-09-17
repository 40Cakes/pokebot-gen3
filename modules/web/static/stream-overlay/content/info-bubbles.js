import config from "../config.js";
import {speciesSprite} from "../helper.js";
import {fetchers} from "../connection.js";

const bubbleContainer = document.querySelector("#info-bubbles");
const infoBubbleAbility = document.querySelector("#info-bubble-ability");
const infoBubbleWhiteFlute = document.querySelector("#info-bubble-white-flute");
const infoBubbleBlackFlute = document.querySelector("#info-bubble-black-flute");
const infoBubbleCleanseTag = document.querySelector("#info-bubble-cleanse-tag");
const infoBubbleRepel = document.querySelector("#info-bubble-repel");
const infoBubbleRepelLevel = document.querySelector("#info-bubble-repel span");
const infoBubbleFailedFishing = document.querySelector("#info-bubble-failed-fishing");
const infoBubbleFailedFishingSprite = document.querySelector("#info-bubble-failed-fishing img:first-of-type");
const infoBubbleFailedFishingCurrent = document.querySelector("#info-bubble-failed-fishing span");
const infoBubbleFailedFishingRecord = document.querySelector("#info-bubble-failed-fishing small");
const infoBubblePokeNav = document.querySelector("#info-bubble-pokenav");
const infoBubblePokeNavCalls = document.querySelector("#info-bubble-pokenav span");
const infoBubblePCStorage = document.querySelector("#info-bubble-pc-storage");
const infoBubblePCStorageNumber = document.querySelector("#info-bubble-pc-storage span");
const infoBubbleCountdown = document.querySelector("#info-bubble-countdown");
const infoBubbleCountdownText = document.querySelector("#info-bubble-countdown span");

/** @type {array<InfoBubble>} */
const customInfoBubbles = [];

const FOSSIL_SPECIES = ["Anorith", "Lileep", "Omanyte", "Kabuto", "Aerodactyl"];

let lastSetAbility = null;
let lastRepelLevel = null;
/** @type {{[k: string]: [HTMLDivElement, HTMLSpanElement, number, number | undefined]}} */
const targetTimerBubbles = {};
/** @type {Date | null} */
let lastFemale = null;
/** @type {number | null} */
let pcStorageTimer = null;
/** @type {number | null} */
let countdownTimer = null;

/**
 * @param {StreamEvents.MapEncounters} mapEncounters
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {string[] | null} targetTimers
 * @param {EncounterType} lastEncounterType
 * @param {Pokemon[]} party
 * @param {number | null} countdownTarget
 */
function updateInfoBubbles(mapEncounters, stats, targetTimers, lastEncounterType, party, countdownTarget) {
    let activeAbility = mapEncounters.active_ability;
    if (lastEncounterType === "hatched") {
        for (const member of party) {
            if (["Magma Armor", "Flame Body"].includes(member.ability.name)) {
                activeAbility = member.ability.name;
                break;
            }
        }
    }

    if (activeAbility !== lastSetAbility) {
        infoBubbleAbility.innerText = "";

        if (activeAbility) {
            infoBubbleAbility.style.display = "block";
            infoBubbleAbility.innerText = activeAbility;

            let sprite = null;
            if (["Magma Armor", "Flame Body"].includes(activeAbility)) {
                for (const member of party) {
                    if (member.ability.name === activeAbility) {
                        sprite = speciesSprite(member.species_name_for_stats, member.is_shiny ? "shiny-cropped" : "normal-cropped", false);
                        sprite.classList.add("icon-species-static");
                        break;
                    }
                }
            } else {
                if (party[0].ability.name === activeAbility) {
                    sprite = speciesSprite(party[0].species_name_for_stats, party[0].is_shiny ? "shiny-cropped" : "normal-cropped", false);
                    sprite.classList.add("icon-species-static");
                }
            }

            if (sprite) {
                infoBubbleAbility.prepend(sprite);
            }
        } else {
            infoBubbleAbility.style.display = "none";
        }
        lastSetAbility = activeAbility;
    }

    if (mapEncounters.repel_level !== lastRepelLevel) {
        if (mapEncounters.repel_level) {
            infoBubbleRepel.style.display = "block";
            infoBubbleRepelLevel.innerText = mapEncounters.repel_level.toString();
        } else {
            infoBubbleRepel.style.display = "none";
        }
        lastRepelLevel = mapEncounters.repel_level;
    }

    infoBubbleWhiteFlute.style.display = mapEncounters.active_items.includes("White Flute") ? "block" : "none";
    infoBubbleBlackFlute.style.display = mapEncounters.active_items.includes("Black Flute") ? "block" : "none";
    infoBubbleCleanseTag.style.display = mapEncounters.active_items.includes("Cleanse Tag") ? "block" : "none";

    let isFirst = true;
    for (const index in targetTimers) {
        const speciesName = targetTimers[index];
        if (targetTimerBubbles.hasOwnProperty(speciesName)) {
            continue;
        }

        const bubble = document.createElement("div");
        bubble.classList.add("info-bubble");

        const sprite = speciesSprite(speciesName, "normal", true);
        sprite.classList.add("icon-species");

        if (FOSSIL_SPECIES.includes(speciesName)) {
            const femaleIcon = document.createElement("img");
            femaleIcon.src = "/static/sprites/other/Female.png";
            femaleIcon.classList.add("icon-female");
            bubble.append(femaleIcon);
        }

        let span = document.createElement("span");
        if (isFirst) {
            bubble.append(span, sprite);
            isFirst = false;
        } else {
            bubble.append(sprite, span);
        }

        targetTimerBubbles[speciesName] = [bubble, span, -1, undefined];
        bubbleContainer.append(bubble);
        updateEncounterInfoBubble(speciesName, stats);
    }
    for (const speciesName of Object.keys(targetTimerBubbles)) {
        if (!targetTimers.includes(speciesName)) {
            targetTimerBubbles[speciesName][0].remove();
            if (targetTimerBubbles[speciesName][3]) {
                window.clearTimeout(targetTimerBubbles[speciesName][3])
            }
            delete targetTimerBubbles[speciesName];
        }
    }

    updateFishingInfoBubble(stats);
    updatePokeNavInfoBubble(stats);

    if (config.showPCStorageCounter && !pcStorageTimer) {
        const updatePCStorageCounter = () => {
            fetchers.pokemonStorageSize().then(data => {
                infoBubblePCStorageNumber.innerText = data.pokemon_stored.toString();
            });
        }

        infoBubblePCStorage.style.display = "inline-block";
        updatePCStorageCounter();
        pcStorageTimer = window.setInterval(updatePCStorageCounter, 10000);
    }

    if (countdownTimer) {
        window.clearInterval(countdownTimer);
        countdownTimer = null;
    }
    if (countdownTarget) {
        let targetTimestamp;
        if (typeof countdownTarget === "string") {
            targetTimestamp = new Date(countdownTarget).getTime();
        } else if (countdownTarget < 10000000000) {
            targetTimestamp = countdownTarget * 1000;
        } else {
            targetTimestamp = countdownTarget;
        }

        if (targetTimestamp > new Date().getTime()) {
            infoBubbleCountdown.style.opacity = "1";
            infoBubbleCountdown.style.display = "inline-block";
            const updateCountdown = () => {
                const now = new Date().getTime();
                const diff = Math.floor((targetTimestamp - now) / 1000);
                if (now < targetTimestamp) {
                    const days = Math.floor(diff / 86400);
                    const hours = Math.floor((diff % 86400) / 3600);
                    const minutes = Math.floor((diff % 3600) / 60);
                    const seconds = Math.floor(diff % 60);

                    const timeString = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`

                    if (days > 0) {
                        if (days > 9) {
                            infoBubbleCountdownText.style.minWidth = "13vh";
                        } else {
                            infoBubbleCountdownText.style.minWidth = "12vh";
                        }
                        infoBubbleCountdownText.innerHTML = `${days.toLocaleString('en')} <small>day${days !== 1 ? 's' : ''}</small> ${timeString}`;
                    } else {
                        infoBubbleCountdownText.style.minWidth = "7.1vh";
                        infoBubbleCountdownText.innerText = timeString;
                    }
                } else {
                    const fadeOutInSeconds = 1.0;

                    infoBubbleCountdownText.innerText = "00:00:00";
                    infoBubbleCountdown.style.opacity = "1";
                    const bbox = infoBubbleCountdown.getBoundingClientRect();
                    infoBubbleCountdown.style.width = `${bbox.width}px`;
                    infoBubbleCountdown.style.height = `${bbox.height}px`;
                    infoBubbleCountdown.style.boxSizing = "border-box";
                    infoBubbleCountdown.style.transition = `opacity ${fadeOutInSeconds}s, width ${fadeOutInSeconds}s, padding ${fadeOutInSeconds}s, margin ${fadeOutInSeconds}s`;
                    infoBubbleCountdown.style.opacity = "0";
                    window.clearInterval(countdownTimer);
                    countdownTimer = null;

                    window.setTimeout(
                        () => {
                            infoBubbleCountdown.style.overflow = "hidden";
                            infoBubbleCountdown.style.width = "0";
                            infoBubbleCountdown.style.padding = "0";
                            infoBubbleCountdown.style.margin = "0 -.5vh";
                        },
                        Math.round(fadeOutInSeconds * 1000));

                    window.setTimeout(
                        () => {
                            infoBubbleCountdown.style.display = "none";
                            infoBubbleCountdown.style.transition = "";
                            infoBubbleCountdown.style.opacity = "1";
                        },
                        Math.round(fadeOutInSeconds * 2000));
                }
            };

            updateCountdown();
            countdownTimer = window.setInterval(updateCountdown, 1000);
        } else {
            infoBubbleCountdown.style.display = "none";
        }
    } else {
        infoBubbleCountdown.style.display = "none";
    }
}

/**
 * @param {string} speciesName
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {"male" | "female" | null} [encounterGender]
 */
function updateEncounterInfoBubble(speciesName, stats, encounterGender) {
    if (!targetTimerBubbles.hasOwnProperty(speciesName)) {
        return;
    }

    if (!stats.pokemon.hasOwnProperty(speciesName)) {
        // targetTimerBubbles[speciesName][0].style.display = "none";
        targetTimerBubbles[speciesName][1].innerText = "never";
        return;
    }

    if (targetTimerBubbles[speciesName][3]) {
        window.clearTimeout(targetTimerBubbles[speciesName][3]);
    }

    let lastEncounterTime = new Date(stats.pokemon[speciesName].last_encounter_time);
    if (FOSSIL_SPECIES.includes(speciesName)) {
        if (encounterGender === "female") {
            lastFemale = new Date();
        }
        lastEncounterTime = lastFemale;

        if (lastEncounterTime === null) {
            targetTimerBubbles[speciesName][1].innerText = "?";
            return;
        }
    }

    const diffInMS = new Date().getTime() - lastEncounterTime.getTime();
    const diffInMinutes = Math.floor(diffInMS / 60000);
    if (targetTimerBubbles[speciesName][2] !== diffInMinutes) {
        targetTimerBubbles[speciesName][2] = diffInMinutes;

        const hours = Math.floor(diffInMinutes / 60);
        const minutes = diffInMinutes % 60;

        if (hours === 0) {
            targetTimerBubbles[speciesName][1].innerHTML = `${minutes.toString()} <small>min</small>`;
        } else {
            targetTimerBubbles[speciesName][1].innerHTML = `${hours} <small>hr</small> ${minutes} <small>min</small>`;
        }
        targetTimerBubbles[speciesName][1].style.display = "inline-block";
    }

    const msUntilNextMinute = ((diffInMinutes + 1) * 60000) - diffInMS;
    targetTimerBubbles[speciesName][3] = window.setTimeout(
        () => updateEncounterInfoBubble(speciesName, stats),
        msUntilNextMinute + 1);
}

/**
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {"Old" | "Good" | "Super"} rod
 */
function updateFishingInfoBubble(stats, rod = "Old") {
    if (stats.current_phase?.current_unsuccessful_fishing_streak > 0) {
        infoBubbleFailedFishingSprite.setAttribute("item", `${rod} Rod`);
        infoBubbleFailedFishing.style.display = "block";
        infoBubbleFailedFishingCurrent.innerText = stats.current_phase.current_unsuccessful_fishing_streak.toLocaleString("en");
        infoBubbleFailedFishingRecord.innerText = `(${stats.current_phase.longest_unsuccessful_fishing_streak.toLocaleString("en")})`;
    } else {
        infoBubbleFailedFishing.style.display = "none";
    }
}

function hideFishingInfoBubble() {
    infoBubbleFailedFishing.style.display = "none";
}

/**
 * @param {PokeBotApi.GetStatsResponse|null} stats
 */
function updatePokeNavInfoBubble(stats) {
    if (stats === null || !stats.current_phase || !config.showPokeNavCallCounter) {
        infoBubblePokeNav.style.display = "none";
    } else if (stats.current_phase.pokenav_calls > 0) {
        infoBubblePokeNav.style.display = "block";
        infoBubblePokeNavCalls.innerText = stats.current_phase.pokenav_calls.toLocaleString("en");
    }
}

/**
 * @param {{info_bubble_id: string, info_bubble_type?: string | null, info_bubble_icon?: string | null, quantity?: number, quantity_target?: number, content?: string}} data
 */
function addInfoBubble(data) {
    if (!customInfoBubbles[data.info_bubble_id]) {
        customInfoBubbles[data.info_bubble_id] = document.createElement("info-bubble");
        bubbleContainer.prepend(customInfoBubbles[data.info_bubble_id]);
    }
    let infoBubble = customInfoBubbles[data.info_bubble_id];

    if (data.info_bubble_type && data.info_bubble_icon && infoBubble.getAttribute("sprite-type") !== data.info_bubble_type && infoBubble.getAttribute("sprite-icon") !== data.info_bubble_icon) {
        customInfoBubbles[data.info_bubble_id].setAttribute("sprite-type", data.info_bubble_type);
        customInfoBubbles[data.info_bubble_id].setAttribute("sprite-icon", data.info_bubble_icon);
    }
    if (data.quantity) {
        customInfoBubbles[data.info_bubble_id].setAttribute("quantity", data.quantity);
        if (data.quantity_target) {
            customInfoBubbles[data.info_bubble_id].setAttribute("quantity-target", data.quantity_target);
        }
    } else if (data.content) {
        customInfoBubbles[data.info_bubble_id].setAttribute("content", data.content);
    }
}

function hideInfoBubble(infoBubbleID) {
    if (customInfoBubbles[infoBubbleID]) {
        customInfoBubbles[infoBubbleID].remove();
        delete customInfoBubbles[infoBubbleID];
    }
}

function resetCustomInfoBubbles() {
    for (const infoBubbleID of Object.keys(customInfoBubbles)) {
        customInfoBubbles[infoBubbleID].remove();
        delete customInfoBubbles[infoBubbleID];
    }
}

export {
    updateInfoBubbles,
    updateEncounterInfoBubble,
    updateFishingInfoBubble,
    hideFishingInfoBubble,
    updatePokeNavInfoBubble,
    addInfoBubble,
    hideInfoBubble,
    resetCustomInfoBubbles,
};
