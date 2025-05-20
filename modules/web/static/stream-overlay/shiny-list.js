import {
    calculatePSP,
    colouredShinyValue,
    diffTime,
    formatInteger, genderSprite,
    getSpriteFor, heldItemSprite, overlaySprite,
    renderTableRow,
    shortInteger
} from "./helper.js";

const tbody = document.querySelector("#shiny-log tbody");

/**
 * @param {PokeBotApi.GetShinyLogResponse} shinyLog
 */
function updateShinyLog(shinyLog) {
    tbody.innerHTML = "";

    for (let index = 0; index < 9; index++) {
        if (shinyLog.length <= index) {
            continue;
        }

        const entry = shinyLog[index];
        const successful =
            entry.shiny_encounter.outcome === "Caught" ||
            entry.shiny_encounter.outcome === "InProgress" ||
            entry.shiny_encounter.outcome === null;

        const speciesSprite = getSpriteFor(entry.shiny_encounter.pokemon.species.name, "shiny");
        if (!successful) {
            speciesSprite.classList.add("unsuccessful");
        }

        tbody.append(renderTableRow({
            timeSinceEncounter: diffTime(entry.phase.end_time),
            sprite: [
                speciesSprite,
                genderSprite(entry.shiny_encounter.pokemon.gender),
                successful
                    ? heldItemSprite(entry.shiny_encounter.pokemon.held_item)
                    : overlaySprite("cross"),
            ],
            shinyValue: colouredShinyValue(entry.shiny_encounter.pokemon.shiny_value),
            phaseEncounters: formatInteger(entry.phase.encounters),
            phaseDuration: diffTime(entry.phase.start_time, entry.phase.end_time),
            psp: calculatePSP(entry.phase.encounters),
            totalSpeciesEncounters: shortInteger(entry.snapshot.species_encounters),
            shinySpeciesEncounters: shortInteger(entry.snapshot.species_shiny_encounters),
            totalEncounters: shortInteger(entry.snapshot.total_encounters),
        }));
    }
}

export {updateShinyLog};
