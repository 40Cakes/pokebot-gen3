import {
    colouredIVSum,
    colouredShinyValue,
    formatInteger,
    speciesSprite,
    renderTableRow,
    br,
    small,
    getSpeciesGoal, overlaySprite, getEmptySpeciesEntry, getSpeciesCatches
} from "../helper.js";

const mapNameSpan = document.querySelector("#route-encounters > h2 > span");
const tbody = document.querySelector("#route-encounters tbody");
const table = document.querySelector("#route-encounters table");
const noEncountersMessage = document.querySelector("#no-encounters-on-this-route-message");

/**
 * @param {PokeBotApi.GetMapResponse} map
 */
const updateMapName = map => {
    mapNameSpan.innerText = map.map.pretty_name;
};

/**
 * @param {PokeBotApi.GetMapEncountersResponse} encounters
 * @param {PokeBotApi.GetStatsResponse} stats
 * @param {EncounterType} encounterType
 * @param {StreamOverlay.SectionChecklist} checklistConfig
 * @param {string} botMode
 * @param {boolean} daycareMode
 * @param {Encounter[]} [encounterLog]
 * @param {Set<string>} [additionalRouteSpecies]
 * @param {string} [animateSpecies]
 */
const updateRouteEncountersList = (encounters, stats, encounterType, checklistConfig, botMode, daycareMode, encounterLog = [], additionalRouteSpecies = null, animateSpecies = null) => {
    /** @type {MapEncounter[]} encounterList */
    let encounterList;
    /** @type {MapEncounter[]} regularEncounterList */
    let regularEncounterList;
    if (daycareMode || botMode.toLowerCase().includes("daycare") || botMode.toLowerCase().includes("kecleon")) {
        encounterList = [];
        regularEncounterList = [];
    } else if (encounterType === "surfing") {
        encounterList = [...encounters.effective.surf_encounters];
        regularEncounterList = [...encounters.regular.surf_encounters];
    } else if (encounterType === "fishing_old_rod") {
        encounterList = [...encounters.effective.old_rod_encounters];
        regularEncounterList = [...encounters.regular.old_rod_encounters];
    } else if (encounterType === "fishing_good_rod") {
        encounterList = [...encounters.effective.good_rod_encounters];
        regularEncounterList = [...encounters.regular.good_rod_encounters];
    } else if (encounterType === "fishing_super_rod") {
        encounterList = [...encounters.effective.super_rod_encounters];
        regularEncounterList = [...encounters.regular.super_rod_encounters];
    } else if (encounterType === "rock_smash") {
        encounterList = [...encounters.effective.rock_smash_encounters];
        regularEncounterList = [...encounters.regular.rock_smash_encounters];
    } else {
        encounterList = [...encounters.effective.land_encounters];
        regularEncounterList = [...encounters.regular.land_encounters];
    }

    // Add species that could appear on this map but are currently blocked by Repel and
    // therefore not part of the 'effective encounters' list.
    for (const regularEncounter of regularEncounterList) {
        let alreadyInList = false;
        for (const encounterSpecies of encounterList) {
            if (encounterSpecies.species_name === regularEncounter.species_name) {
                alreadyInList = true;
            }
        }

        if (!alreadyInList) {
            encounterList.push({
                species_name: regularEncounter.species_name,
                max_level: regularEncounter.max_level,
                encounter_rate: 0
            });
        }
    }

    // Add species to this list that have been encountered here but are not part of the
    // regular encounter table (i.e. egg hatches, gift Pokémon, ...)
    for (const speciesName of additionalRouteSpecies) {
        let alreadyInList = false;
        for (const encounterSpecies of encounterList) {
            if (encounterSpecies.species_name === speciesName) {
                alreadyInList = true;
            }
        }

        if (!alreadyInList) {
            encounterList.push({species_name: speciesName, encounter_rate: 0});
        }
    }

    if (botMode.toLowerCase().includes("feebas") && ["surfing", "fishing_old_rod", "fishing_good_rod", "fishing_super_rod"].includes(encounterType)) {
        let hasRecentlySeenFeebas = false;
        for (const recentEncounter of encounterLog) {
            if (recentEncounter.pokemon.species.name === "Feebas") {
                hasRecentlySeenFeebas = true;
                break;
            }
        }

        if (hasRecentlySeenFeebas) {
            let newEncounterList = [];
            for (const encounter of encounterList) {
                const newEncounter = {...encounter};
                newEncounter.encounter_rate /= 2;
                newEncounterList.push(newEncounter);
            }
            newEncounterList.push({
                species_id: 328,
                species_name: "Feebas",
                min_level: 20,
                max_level: 25,
                encounter_rate: 0.5
            });
            encounterList = newEncounterList;
        }
    }

    // Display a 'no encounters on this map' message if no encounters exist at all.
    if (encounterList.length === 0) {
        noEncountersMessage.style.display = "block";
        table.style.display = "none";
        return;
    }

    noEncountersMessage.style.display = "none";
    table.style.display = "table";

    tbody.innerHTML = "";

    let hasAtLeastOneAnti = false;
    let hasPossibleEncounterThatIsNotAnti = false;
    for (const encounter of encounterList) {
        const species = stats.pokemon[encounter.species_name] ?? getEmptySpeciesEntry(encounter.species_id, encounter.species_name);
        const currentPhase = stats.current_phase;

        let catches = "0";
        let totalEncounters = "0";

        const goal = getSpeciesGoal(encounter.species_name, checklistConfig, stats);
        if (goal) {
            catches = [getSpeciesCatches(encounter.species_name, checklistConfig, stats), small(`/${goal}`)];
        } else {
            catches = [formatInteger(species.catches)];
        }
        totalEncounters = [formatInteger(species.total_encounters)];

        if (species.shiny_encounters > 0) {
            const shinyRate = Math.round(species.total_encounters / species.shiny_encounters).toLocaleString("en");
            const shinyRateLabel = document.createElement("span");
            shinyRateLabel.classList.add("shiny-rate");
            const sparkles = overlaySprite("sparkles");
            shinyRateLabel.append("(", sparkles, ` 1/${shinyRate})`);
            totalEncounters.push(shinyRateLabel);
        }

        if (species.shiny_encounters > species.catches) {
            const missedShinies = species.shiny_encounters - species.catches;
            const missedShiniesLabel = document.createElement("span");
            missedShiniesLabel.classList.add("missed-shinies")
            missedShiniesLabel.textContent = `(${formatInteger(missedShinies)} missed)`;
            catches.push(missedShiniesLabel);
        }

        if (goal && species.catches >= goal) {
            const tick = document.createElement("img")
            tick.src = "/static/sprites/stream-overlay/tick.png";
            tick.classList.add("tick");
            catches.push(tick);
        } else if (goal) {
            const tick = document.createElement("img")
            tick.src = "/static/sprites/stream-overlay/target.png";
            tick.classList.add("tick");
            catches.push(tick);
        }

        let spriteType = "normal";
        let animate = encounter.species_name === animateSpecies;
        if (species && species.phase_highest_sv > 65527) {
            spriteType = "anti-shiny";
            hasAtLeastOneAnti = true;
        }
        if (encounter.encounter_rate > 0 && (!species || species.phase_highest_sv < 65528)) {
            hasPossibleEncounterThatIsNotAnti = true;
        }
        if (species && encounter.encounter_rate <= 0 && hasAtLeastOneAnti && !hasPossibleEncounterThatIsNotAnti) {
            spriteType = "anti-shiny";
        }

        tbody.append(renderTableRow({
            sprite: speciesSprite(encounter.species_name, spriteType, animate),
            odds: encounter.encounter_rate > 0 ? Math.round(encounter.encounter_rate * 100) + "%" : "",
            svRecords: species && species.phase_lowest_sv && species.phase_highest_sv
                ? [colouredShinyValue(species.phase_lowest_sv), br(), colouredShinyValue(species.phase_highest_sv)]
                : "",
            ivRecords: species && species.phase_highest_iv_sum && species.phase_lowest_iv_sum
                ? [colouredIVSum(species.phase_highest_iv_sum), br(), colouredIVSum(species.phase_lowest_iv_sum)]
                : "",
            phaseEncounters: species && species.phase_encounters > 0 && currentPhase.encounters > 0
                ? [
                    formatInteger(species.phase_encounters),
                    br(),
                    small((100 * species.phase_encounters / currentPhase.encounters).toLocaleString("en", {maximumFractionDigits: 2}) + "%"),
                ]
                : "0",
            totalEncounters: totalEncounters,
            catches: catches,
        }));
    }
};

export {updateMapName, updateRouteEncountersList};
