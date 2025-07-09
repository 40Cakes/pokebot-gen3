import {
    calculatePSP,
    colouredShinyValue,
    diffTime,
    formatInteger, genderSprite,
    speciesSprite, itemSprite, overlaySprite,
    renderTableRow,
    shortInteger, emptyTableRow, numberOfEncounterLogEntries
} from "../helper.js";

const tbody = document.querySelector("#shiny-log tbody");

/**
 * @param {PokeBotApi.GetShinyLogResponse} shinyLog
 */
function updateShinyLog(shinyLog) {
    tbody.innerHTML = "";

    for (let index = 0; index < numberOfEncounterLogEntries; index++) {
        if (shinyLog.length <= index) {
            tbody.append(emptyTableRow(9));
            continue;
        }

        const entry = shinyLog[index];
        const successful =
            entry.shiny_encounter.outcome === "Caught" ||
            entry.shiny_encounter.outcome === "InProgress" ||
            entry.shiny_encounter.outcome === null;

        const sprite = speciesSprite(entry.shiny_encounter.pokemon.species_name_for_stats, "shiny");
        if (!successful) {
            sprite.classList.add("unsuccessful");
        }

        tbody.append(renderTableRow({
            timeSinceEncounter: diffTime(entry.phase.end_time, null, true),
            sprite: [
                sprite,
                genderSprite(entry.shiny_encounter.pokemon.gender),
                successful
                    ? itemSprite(entry.shiny_encounter.pokemon.held_item)
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
