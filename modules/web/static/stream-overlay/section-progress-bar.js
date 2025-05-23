import {clamp} from "./helper.js";

const div = document.querySelector("div#section-progress-bar");

/**
 * @param {StreamOverlay.Config.speciesChecklist} speciesChecklist
 * @param {PokeBotApi.GetStatsResponse} stats
 */
function updateSectionProgressBar(speciesChecklist, stats) {
    let goal = 0;
    let caught = 0;
    for (const [checklistSpeciesName, checklistEntry] of Object.entries(speciesChecklist)) {
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

    const percentage = goal > 0 ? Math.round(100 * caught / goal) : 0;

    const filled = document.createElement("div");
    filled.style.width = `${percentage}%`;

    if (percentage === 100) {
        filled.classList.add("green");
    } else {
        filled.classList.add("yellow");
    }

    div.innerHTML = "";
    div.append(filled);
}

export {updateSectionProgressBar};
