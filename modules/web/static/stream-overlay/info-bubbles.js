import {getSpriteFor, small} from "./helper.js";

const bubbleContainer = document.querySelector("#info-bubbles");
const infoBubbleAbility = document.querySelector("#info-bubble-ability");
const infoBubbleWhiteFlute = document.querySelector("#info-bubble-white-flute");
const infoBubbleBlackFlute = document.querySelector("#info-bubble-black-flute");
const infoBubbleCleanseTag = document.querySelector("#info-bubble-cleanse-tag");
const infoBubbleRepel = document.querySelector("#info-bubble-repel");
const infoBubbleRepelLevel = document.querySelector("#info-bubble-repel span");

let lastSetAbility = null;
let lastRepelLevel = null;
/** @type {{[k: string]: [HTMLDivElement, HTMLSpanElement, number, number | undefined]}} */
const targetTimerBubbles = {};

/**
 * @param {StreamEvents.MapEncounters} mapEncounters
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {string[] | null} targetTimers
 */
function updateInfoBubbles(mapEncounters, stats, targetTimers) {
    if (mapEncounters.active_ability !== lastSetAbility) {
        if (mapEncounters.active_ability) {
            infoBubbleAbility.style.display = "block";
            infoBubbleAbility.innerText = mapEncounters.active_ability;
        } else {
            infoBubbleAbility.style.display = "none";
        }
        lastSetAbility = mapEncounters.active_ability;
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
        const bubble = document.createElement("div");
        bubble.classList.add("info-bubble");

        const sprite = getSpriteFor(speciesName, "normal", true);
        sprite.classList.add("icon-species");
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
}

/**
 * @param {string} speciesName
 * @param {PokeBotApi.GetStatsResponse} stats
 */
function updateEncounterInfoBubble(speciesName, stats) {
    if (!targetTimerBubbles.hasOwnProperty(speciesName)) {
        return;
    }

    if (!stats.pokemon.hasOwnProperty(speciesName)) {
        targetTimerBubbles[speciesName][1].innerText = "?";
        return;
    }

    if (targetTimerBubbles[speciesName][3]) {
        window.clearTimeout(targetTimerBubbles[speciesName][3]);
    }

    const diffInMS = new Date().getTime() - new Date(stats.pokemon[speciesName].last_encounter_time).getTime();
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
    }

    const msUntilNextMinute = ((diffInMinutes + 1) * 60000) - diffInMS;
    window.setTimeout(() => updateEncounterInfoBubble(speciesName, stats), msUntilNextMinute + 1)
}

export {updateInfoBubbles, updateEncounterInfoBubble};
