import config from "../config.js";
import {speciesSprite} from "../helper.js";

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

const FOSSIL_SPECIES = ["Anorith", "Lileep", "Omanyte", "Kabuto", "Aerodactyl"];

let lastSetAbility = null;
let lastRepelLevel = null;
/** @type {{[k: string]: [HTMLDivElement, HTMLSpanElement, number, number | undefined]}} */
const targetTimerBubbles = {};
/** @type {Date | null} */
let lastFemale = null;

/**
 * @param {StreamEvents.MapEncounters} mapEncounters
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {string[] | null} targetTimers
 * @param {EncounterType} lastEncounterType
 * @param {Pokemon[]} party
 */
function updateInfoBubbles(mapEncounters, stats, targetTimers, lastEncounterType, party) {
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

    updateFishingInfoBubble(stats);
    updatePokeNavInfoBubble(stats);
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
        targetTimerBubbles[speciesName][0].style.display = "none";
        targetTimerBubbles[speciesName][1].innerText = "?";
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

export {
    updateInfoBubbles,
    updateEncounterInfoBubble,
    updateFishingInfoBubble,
    hideFishingInfoBubble,
    updatePokeNavInfoBubble
};
