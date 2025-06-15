import {colouredIV, colouredIVSum, colouredShinyValue} from "../helper.js";

const encounterStats = document.querySelector("#encounter-stats");
const encounterSVContainer = document.querySelector("#encounter-sv");

const encounterPersonality = document.querySelector("#encounter-stats td:nth-child(1)");
const encounterItem = document.querySelector("#encounter-stats td:nth-child(2)");
const encounterHPIV = document.querySelector("#encounter-stats td:nth-child(3)");
const encounterAttackIV = document.querySelector("#encounter-stats td:nth-child(4)");
const encounterDefenceIV = document.querySelector("#encounter-stats td:nth-child(5)");
const encounterSpecialAttackIV = document.querySelector("#encounter-stats td:nth-child(6)");
const encounterSpecialDefenceIV = document.querySelector("#encounter-stats td:nth-child(7)");
const encounterSpeedIV = document.querySelector("#encounter-stats td:nth-child(8)");
const encounterIVSum = document.querySelector("#encounter-stats td:nth-child(9)");
const encounterNature = document.querySelector("#encounter-stats td:nth-child(10)");
const encounterSV = document.querySelector("#encounter-sv td");

/**
 * @param {Encounter} encounter
 */
function showCurrentEncounterStats(encounter) {
    encounterPersonality.textContent = "";
    encounterItem.textContent = "";
    encounterHPIV.textContent = "";
    encounterAttackIV.textContent = "";
    encounterDefenceIV.textContent = "";
    encounterSpecialAttackIV.textContent = "";
    encounterSpecialDefenceIV.textContent = "";
    encounterSpeedIV.textContent = "";
    encounterIVSum.textContent = "";
    encounterNature.textContent = "";
    encounterSV.textContent = "";

    encounterPersonality.textContent = encounter.pokemon.personality_value.toString(16).padStart(8, "0");

    const ivLabel = key => {
        const result = [colouredIV(encounter.pokemon.ivs[key])];
        if (encounter.pokemon.nature.modifiers[key] > 1) {
            const arrowSprite = document.createElement("img");
            arrowSprite.src = "../sprites/stream-overlay/arrow_green.png";
            arrowSprite.classList.add("arrow-sprite");
            arrowSprite.classList.add("arrow-upside-down");
            result.push(arrowSprite);
        } else if (encounter.pokemon.nature.modifiers[key] < 1) {
            const arrowSprite = document.createElement("img");
            arrowSprite.src = "../sprites/stream-overlay/arrow_red.png";
            arrowSprite.classList.add("arrow-sprite");
            result.push(arrowSprite);
        }
        return result;
    };

    encounterHPIV.append(...ivLabel("hp"));
    encounterAttackIV.append(...ivLabel("attack"));
    encounterDefenceIV.append(...ivLabel("defence"));
    encounterSpecialAttackIV.append(...ivLabel("special_attack"));
    encounterSpecialDefenceIV.append(...ivLabel("special_defence"));
    encounterSpeedIV.append(...ivLabel("speed"));
    encounterIVSum.append(colouredIVSum(encounter.pokemon.ivs.hp +
        encounter.pokemon.ivs.attack +
        encounter.pokemon.ivs.defence +
        encounter.pokemon.ivs.special_attack +
        encounter.pokemon.ivs.special_defence +
        encounter.pokemon.ivs.speed));
    encounterNature.append(encounter.pokemon.nature.name);

    if (encounter.pokemon.held_item) {
        const heldItemSprite = document.createElement("img");
        heldItemSprite.src = `../sprites/items/${encounter.pokemon.held_item.name}.png`;
        heldItemSprite.classList.add("item-sprite");
        encounterItem.append(heldItemSprite);
    }

    const svSprite = document.createElement("img");
    svSprite.classList.add("sv-sprite");
    if (encounter.pokemon.is_shiny) {
        svSprite.src = "../sprites/stream-overlay/sparkles.png";
    } else if (encounter.pokemon.is_anti_shiny) {
        svSprite.src = "../sprites/stream-overlay/anti-sparkles.png";
    } else {
        svSprite.src = "../sprites/stream-overlay/cross.png";
    }
    encounterSV.append(colouredShinyValue(encounter.pokemon.shiny_value), svSprite);

    encounterStats.style.display = "block";
    encounterSVContainer.style.display = "block";
}

function hideCurrentEncounterStats() {
    encounterStats.style.display = "none";
    encounterSVContainer.style.display = "none";
}

export {showCurrentEncounterStats, hideCurrentEncounterStats};
