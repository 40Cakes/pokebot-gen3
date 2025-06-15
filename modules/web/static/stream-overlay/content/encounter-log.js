import {
    colouredIV,
    colouredIVSum,
    colouredShinyValue,
    genderSprite,
    speciesSprite,
    itemSprite,
    renderTableRow, numberOfEncounterLogEntries, emptyTableRow
} from "../helper.js";

const tbody = document.querySelector("#encounter-log tbody");

/**
 * @param {PokeBotApi.GetEncounterLogResponse} encounterLog
 */
function updateEncounterLog(encounterLog) {
    tbody.innerHTML = "";

    for (let index = 0; index < numberOfEncounterLogEntries; index++) {
        if (encounterLog.length <= index) {
            tbody.append(emptyTableRow(9));
            continue;
        }

        const entry = encounterLog[index];
        const ivSum =
            entry.pokemon.ivs.hp +
            entry.pokemon.ivs.attack +
            entry.pokemon.ivs.defence +
            entry.pokemon.ivs.special_attack +
            entry.pokemon.ivs.special_defence +
            entry.pokemon.ivs.speed;

        tbody.append(renderTableRow({
            sprite: [
                speciesSprite(entry.pokemon.species.name, entry.pokemon.is_shiny ? "shiny" : "normal"),
                genderSprite(entry.pokemon.gender),
                itemSprite(entry.pokemon.held_item),
            ],
            hpIV: colouredIV(entry.pokemon.ivs.hp),
            attackIV: colouredIV(entry.pokemon.ivs.attack, entry.pokemon.nature.modifiers.attack),
            defenceIV: colouredIV(entry.pokemon.ivs.defence, entry.pokemon.nature.modifiers.defence),
            specialAttackIV: colouredIV(entry.pokemon.ivs.special_attack, entry.pokemon.nature.modifiers.special_attack),
            specialDefenceIV: colouredIV(entry.pokemon.ivs.special_defence, entry.pokemon.nature.modifiers.special_defence),
            speedIV: colouredIV(entry.pokemon.ivs.speed, entry.pokemon.nature.modifiers.speed),
            ivSum: colouredIVSum(ivSum),
            shinyValue: colouredShinyValue(entry.pokemon.shiny_value),
        }));
    }
}

export {updateEncounterLog};
