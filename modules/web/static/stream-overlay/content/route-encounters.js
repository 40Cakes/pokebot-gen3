import {
    br,
    colouredIVSum,
    colouredShinyValue,
    formatInteger,
    getEmptySpeciesEntry,
    getSpeciesCatches,
    getSpeciesGoal,
    overlaySprite,
    renderTableRow,
    small,
    speciesSprite
} from "../helper.js";

const mapNameSpan = document.querySelector("#map-name");
const antiShinyCounter = document.querySelector("#anti-shiny-counter");
const tbody = document.querySelector("#route-encounters tbody");
const table = document.querySelector("#route-encounters table");
const noEncountersMessage = document.querySelector("#no-encounters-on-this-route-message");

const ALTERNATIVE_SPECIES = {
    "Ivysaur": ["Bulbasaur"],
    "Venusaur": ["Ivysaur", "Bulbasaur"],
    "Charmeleon": ["Charmander"],
    "Charizard": ["Charmeleon", "Charmander"],
    "Wartortle": ["Squirtle"],
    "Blastoise": ["Wartortle", "Squirtle"],
    "Metapod": ["Caterpie"],
    "Butterfree": ["Metapod", "Caterpie"],
    "Kakuna": ["Weedle"],
    "Beedrill": ["Kakuna", "Weedle"],
    "Pidgeotto": ["Pidgey"],
    "Pidgeot": ["Pidgeotto", "Pidgey"],
    "Raticate": ["Rattata"],
    "Fearow": ["Spearow"],
    "Arbok": ["Ekans"],
    "Pikachu": ["Pichu"],
    "Raichu": ["Pikachu", "Pichu"],
    "Sandslash": ["Sandshrew"],
    "Nidorina": ["Nidoran♀"],
    "Nidoqueen": ["Nidorina", "Nidoran♀"],
    "Nidorino": ["Nidoran♂"],
    "Nidoking": ["Nidorino", "Nidoran♂"],
    "Clefairy": ["Cleffa"],
    "Clefable": ["Clefairy", "Cleffa"],
    "Ninetales": ["Vulpix"],
    "Jigglypuff": ["Igglybuff"],
    "Wigglytuff": ["Jigglypuff", "Igglybuff"],
    "Golbat": ["Zubat"],
    "Gloom": ["Oddish"],
    "Vileplume": ["Gloom", "Oddish"],
    "Parasect": ["Paras"],
    "Venomoth": ["Venonat"],
    "Dugtrio": ["Diglett"],
    "Persian": ["Meowth"],
    "Golduck": ["Psyduck"],
    "Primeape": ["Mankey"],
    "Arcanine": ["Growlithe"],
    "Poliwhirl": ["Poliwag"],
    "Poliwrath": ["Poliwhirl", "Poliwag"],
    "Kadabra": ["Abra"],
    "Alakazam": ["Kadabra", "Abra"],
    "Machoke": ["Machop"],
    "Machamp": ["Machoke", "Machop"],
    "Weepinbell": ["Bellsprout"],
    "Victreebel": ["Weepinbell", "Bellsprout"],
    "Tentacruel": ["Tentacool"],
    "Graveler": ["Geodude"],
    "Golem": ["Graveler", "Geodude"],
    "Rapidash": ["Ponyta"],
    "Slowbro": ["Slowpoke"],
    "Magneton": ["Magnemite"],
    "Dodrio": ["Doduo"],
    "Dewgong": ["Seel"],
    "Muk": ["Grimer"],
    "Cloyster": ["Shellder"],
    "Haunter": ["Gastly"],
    "Gengar": ["Haunter", "Gastly"],
    "Hypno": ["Drowzee"],
    "Kingler": ["Krabby"],
    "Electrode": ["Voltorb"],
    "Exeggutor": ["Exeggcute"],
    "Marowak": ["Cubone"],
    "Hitmonlee": ["Tyrogue"],
    "Hitmonchan": ["Tyrogue"],
    "Weezing": ["Koffing"],
    "Rhydon": ["Rhyhorn"],
    "Seadra": ["Horsea"],
    "Seaking": ["Goldeen"],
    "Starmie": ["Staryu"],
    "Jynx": ["Smoochum"],
    "Electabuzz": ["Elekid"],
    "Magmar": ["Magby"],
    "Gyarados": ["Magikarp"],
    "Vaporeon": ["Eevee"],
    "Jolteon": ["Eevee"],
    "Flareon": ["Eevee"],
    "Omastar": ["Omanyte"],
    "Kabutops": ["Kabuto"],
    "Dragonair": ["Dratini"],
    "Dragonite": ["Dragonair", "Dratini"],
    "Bayleef": ["Chikorita"],
    "Meganium": ["Bayleef", "Chikorita"],
    "Quilava": ["Cyndaquil"],
    "Typhlosion": ["Quilava", "Cyndaquil"],
    "Croconaw": ["Totodile"],
    "Feraligatr": ["Croconaw", "Totodile"],
    "Furret": ["Sentret"],
    "Noctowl": ["Hoothoot"],
    "Ledian": ["Ledyba"],
    "Ariados": ["Spinarak"],
    "Crobat": ["Golbat", "Zubat"],
    "Lanturn": ["Chinchou"],
    "Togetic": ["Togepi"],
    "Xatu": ["Natu"],
    "Flaaffy": ["Mareep"],
    "Ampharos": ["Flaaffy", "Mareep"],
    "Bellossom": ["Gloom", "Oddish"],
    "Marill": ["Azurill"],
    "Azumarill": ["Marill", "Azurill"],
    "Politoed": ["Poliwhirl", "Poliwag"],
    "Skiploom": ["Hoppip"],
    "Jumpluff": ["Skiploom", "Hoppip"],
    "Sunflora": ["Sunkern"],
    "Quagsire": ["Wooper"],
    "Espeon": ["Eevee"],
    "Umbreon": ["Eevee"],
    "Slowking": ["Slowpoke"],
    "Wobbuffet": ["Wynaut"],
    "Forretress": ["Pineco"],
    "Steelix": ["Onix"],
    "Granbull": ["Snubbull"],
    "Scizor": ["Scyther"],
    "Ursaring": ["Teddiursa"],
    "Magcargo": ["Slugma"],
    "Piloswine": ["Swinub"],
    "Octillery": ["Remoraid"],
    "Houndoom": ["Houndour"],
    "Kingdra": ["Seadra", "Horsea"],
    "Donphan": ["Phanpy"],
    "Porygon2": ["Porygon"],
    "Hitmontop": ["Tyrogue"],
    "Blissey": ["Chansey"],
    "Pupitar": ["Larvitar"],
    "Tyranitar": ["Pupitar", "Larvitar"],
    "Grovyle": ["Treecko"],
    "Sceptile": ["Grovyle", "Treecko"],
    "Combusken": ["Torchic"],
    "Blaziken": ["Combusken", "Torchic"],
    "Marshtomp": ["Mudkip"],
    "Swampert": ["Marshtomp", "Mudkip"],
    "Mightyena": ["Poochyena"],
    "Linoone": ["Zigzagoon"],
    "Silcoon": ["Wurmple"],
    "Beautifly": ["Silcoon", "Wurmple"],
    "Cascoon": ["Wurmple"],
    "Dustox": ["Cascoon", "Wurmple"],
    "Lombre": ["Lotad"],
    "Ludicolo": ["Lombre", "Lotad"],
    "Nuzleaf": ["Seedot"],
    "Shiftry": ["Nuzleaf", "Seedot"],
    "Ninjask": ["Nincada"],
    "Shedinja": ["Nincada"],
    "Swellow": ["Taillow"],
    "Breloom": ["Shroomish"],
    "Pelipper": ["Wingull"],
    "Masquerain": ["Surskit"],
    "Wailord": ["Wailmer"],
    "Delcatty": ["Skitty"],
    "Claydol": ["Baltoy"],
    "Whiscash": ["Barboach"],
    "Crawdaunt": ["Corphish"],
    "Milotic": ["Feebas"],
    "Sharpedo": ["Carvanha"],
    "Vibrava": ["Trapinch"],
    "Flygon": ["Vibrava", "Trapinch"],
    "Hariyama": ["Makuhita"],
    "Manectric": ["Electrike"],
    "Camerupt": ["Numel"],
    "Sealeo": ["Spheal"],
    "Walrein": ["Sealeo", "Spheal"],
    "Cacturne": ["Cacnea"],
    "Glalie": ["Snorunt"],
    "Grumpig": ["Spoink"],
    "Medicham": ["Meditite"],
    "Altaria": ["Swablu"],
    "Dusclops": ["Duskull"],
    "Vigoroth": ["Slakoth"],
    "Slaking": ["Vigoroth", "Slakoth"],
    "Swalot": ["Gulpin"],
    "Loudred": ["Whismur"],
    "Exploud": ["Loudred", "Whismur"],
    "Huntail": ["Clamperl"],
    "Gorebyss": ["Clamperl"],
    "Banette": ["Shuppet"],
    "Lairon": ["Aron"],
    "Aggron": ["Lairon", "Aron"],
    "Cradily": ["Lileep"],
    "Armaldo": ["Anorith"],
    "Kirlia": ["Ralts"],
    "Gardevoir": ["Kirlia", "Ralts"],
    "Shelgon": ["Bagon"],
    "Salamence": ["Shelgon", "Bagon"],
    "Metang": ["Beldum"],
    "Metagross": ["Metang", "Beldum"]
};

/**
 * @param {PokeBotApi.GetMapResponse} map
 */
const updateMapName = map => {
    mapNameSpan.innerText = map.map.pretty_name;
};

const animateRouteEncounterSprite = (speciesName) => {
    for (const entry of cachedRouteEncountersList) {
        if (entry.speciesName === speciesName && entry.spriteElement) {
            entry.spriteElement.animate();
        }
    }
};

/**
 * @param {OverlayState} state
 * @return {MapEncounter[]}
 */
const getEncounterList = (state) => {
    /** @type {MapEncounter[]} encounterList */
    let encounterList;
    /** @type {MapEncounter[]} regularEncounterList */
    let regularEncounterList;

    if (
        state.daycareMode ||
        state.emulator.bot_mode.toLowerCase().includes("daycare") ||
        state.emulator.bot_mode.toLowerCase().includes("kecleon")
    ) {
        encounterList = [];
        regularEncounterList = [];
    } else if (state.lastEncounterType === "surfing") {
        encounterList = [...state.mapEncounters.effective.surf_encounters];
        regularEncounterList = [...state.mapEncounters.regular.surf_encounters];
    } else if (state.lastEncounterType === "fishing_old_rod") {
        encounterList = [...state.mapEncounters.effective.old_rod_encounters];
        regularEncounterList = [...state.mapEncounters.regular.old_rod_encounters];
    } else if (state.lastEncounterType === "fishing_good_rod") {
        encounterList = [...state.mapEncounters.effective.good_rod_encounters];
        regularEncounterList = [...state.mapEncounters.regular.good_rod_encounters];
    } else if (state.lastEncounterType === "fishing_super_rod") {
        encounterList = [...state.mapEncounters.effective.super_rod_encounters];
        regularEncounterList = [...state.mapEncounters.regular.super_rod_encounters];
    } else if (state.lastEncounterType === "rock_smash") {
        encounterList = [...state.mapEncounters.effective.rock_smash_encounters];
        regularEncounterList = [...state.mapEncounters.regular.rock_smash_encounters];
    } else {
        encounterList = [...state.mapEncounters.effective.land_encounters];
        regularEncounterList = [...state.mapEncounters.regular.land_encounters];
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
    for (const speciesName of state.additionalRouteSpecies) {
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

    if (state.emulator.bot_mode.toLowerCase().includes("feebas") && ["surfing", "fishing_old_rod", "fishing_good_rod", "fishing_super_rod"].includes(state.lastEncounterType)) {
        let hasRecentlySeenFeebas = false;
        for (const recentEncounter of state.encounterLog) {
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

            return newEncounterList;
        }
    }

    return encounterList;
}

/**
 * @typedef {object} RouteEncounterEntry
 * @property {HTMLTableRowElement | null} element
 * @property {PokemonSprite | null} spriteElement
 * @property {string} speciesName
 * @property {boolean} isAnti
 * @property {number} encounterRate
 * @property {number | null} highestSV
 * @property {number | null} lowestSV
 * @property {number | null} highestIVSum
 * @property {number | null} lowestIVSum
 * @property {number} phaseEncounters
 * @property {number | null} phaseEncounterShare
 * @property {number} totalEncounters
 * @property {number | null} shinyRateDivisor
 * @property {number} shiniesObtained
 * @property {number} shinyTargetCount
 * @property {number} missedShinies
 */

/** @type {RouteEncounterEntry[]} cachedRouteEncountersList */
let cachedRouteEncountersList = [];

let cachedAntiShinyCount = 0;

/**
 * @param {RouteEncounterEntry[]} encountersList
 */
const renderRouteEncountersList = (encountersList) => {
    const renderEncounterRate = (rate) => {
        if (rate === 0) {
            return [""];
        } else {
            return [Math.round(rate * 100) + "%"];
        }
    };

    const renderSVRecords = (highest, lowest) => {
        if (highest === null || lowest === null) {
            return [""];
        } else {
            return [colouredShinyValue(lowest), br(), colouredShinyValue(highest)];
        }
    };

    const renderIVRecords = (highest, lowest) => {
        if (highest === null || lowest === null) {
            return [""];
        } else {
            return [colouredIVSum(highest), br(), colouredIVSum(lowest)];
        }
    };

    const renderPhaseEncounters = (encounters, fraction) => {
        if (encounters === 0) {
            return ["0"];
        } else {
            return [
                formatInteger(encounters),
                br(),
                small((100 * fraction).toLocaleString("en", {maximumFractionDigits: 2}) + "%"),
            ];
        }
    };

    const renderTotalEncounters = (totalEncounters, shinyRateDivisor) => {
        if (shinyRateDivisor === null) {
            return [formatInteger(totalEncounters)];
        } else {
            const shinyRateLabel = document.createElement("span");
            shinyRateLabel.classList.add("shiny-rate");
            const sparkles = overlaySprite("sparkles");
            shinyRateLabel.append("(", sparkles, ` 1/${formatInteger(shinyRateDivisor)})`);
            return [formatInteger(totalEncounters), shinyRateLabel];
        }
    };

    const renderCatchCount = (catches, goal, misses) => {
        const result = [catches.toString()];
        if (goal > 0) {
            result.push(small(`/${goal}`));
        }
        if (misses > 0) {
            const missedShiniesLabel = document.createElement("span");
            missedShiniesLabel.classList.add("missed-shinies")
            missedShiniesLabel.textContent = `(${formatInteger(misses)} missed)`;
            result.push(missedShiniesLabel);
        }

        if (goal > 0 && catches >= goal) {
            const tick = document.createElement("img")
            tick.src = "/static/sprites/stream-overlay/tick.png";
            tick.classList.add("tick");
            result.push(tick);
        } else if (goal > 0) {
            const tick = document.createElement("img")
            tick.src = "/static/sprites/stream-overlay/target.png";
            tick.classList.add("tick");
            result.push(tick);
        }

        return result;
    };

    while (cachedRouteEncountersList.length > encountersList.length) {
        const entry = cachedRouteEncountersList.pop();
        entry.element.remove();
    }

    while (encountersList.length > cachedRouteEncountersList.length) {
        const entry = encountersList[cachedRouteEncountersList.length];
        const sprite = speciesSprite(entry.speciesName, entry.isAnti ? "anti-shiny" : "normal");
        const row = renderTableRow({
            sprite: sprite,
            rate: renderEncounterRate(entry.encounterRate),
            svRecords: renderSVRecords(entry.highestSV, entry.lowestSV),
            ivRecords: renderIVRecords(entry.highestIVSum, entry.lowestIVSum),
            phaseEncounters: renderPhaseEncounters(entry.phaseEncounters, entry.phaseEncounterShare),
            totalEncounters: renderTotalEncounters(entry.totalEncounters, entry.shinyRateDivisor),
            catches: renderCatchCount(entry.shiniesObtained, entry.shinyTargetCount, entry.missedShinies),
        });
        tbody.append(row);
        entry.element = row;
        entry.spriteElement = sprite;
        cachedRouteEncountersList.push(entry);
    }

    for (let index = 0; index < encountersList.length; index++) {
        const entry = encountersList[index];
        const cached = cachedRouteEncountersList[index];
        const row = cached.element;

        if (entry.speciesName !== cached.speciesName || entry.isAnti !== cached.isAnti) {
            cached.spriteElement.remove();
            cached.spriteElement = speciesSprite(entry.speciesName, entry.isAnti ? "anti-shiny" : "normal");
            row.children[0].textContent = "";
            row.children[0].append(cached.spriteElement);
        }

        if (entry.encounterRate !== cached.encounterRate) {
            cached.encounterRate = entry.encounterRate;
            row.children[1].textContent = "";
            row.children[1].append(...renderEncounterRate(entry.encounterRate));
        }

        if (entry.lowestSV !== cached.lowestSV || entry.highestSV !== cached.highestSV) {
            cached.lowestSV = entry.lowestSV;
            cached.highestSV = entry.highestSV;
            row.children[2].textContent = "";
            row.children[2].append(...renderSVRecords(entry.highestSV, entry.lowestSV));
        }

        if (entry.lowestIVSum !== cached.lowestIVSum || entry.highestIVSum !== cached.highestIVSum) {
            cached.lowestIVSum = entry.lowestIVSum;
            cached.highestIVSum = entry.highestIVSum;
            row.children[3].textContent = "";
            row.children[3].append(...renderIVRecords(entry.highestIVSum, entry.lowestIVSum));
        }

        if (entry.phaseEncounters !== cached.phaseEncounters || entry.phaseEncounterShare !== cached.phaseEncounterShare) {
            cached.phaseEncounters = entry.phaseEncounters;
            cached.phaseEncounterShare = entry.phaseEncounterShare;
            row.children[4].textContent = "";
            row.children[4].append(...renderPhaseEncounters(entry.phaseEncounters, entry.phaseEncounterShare));
        }

        if (entry.totalEncounters !== cached.totalEncounters || entry.shinyRateDivisor !== cached.shinyRateDivisor) {
            cached.totalEncounters = entry.totalEncounters;
            cached.shinyRateDivisor = entry.shinyRateDivisor;
            row.children[5].textContent = "";
            row.children[5].append(...renderTotalEncounters(entry.totalEncounters, entry.shinyRateDivisor));
        }

        if (entry.shiniesObtained !== cached.shiniesObtained || entry.shinyTargetCount !== cached.shinyTargetCount || entry.missedShinies !== cached.missedShinies) {
            cached.shiniesObtained = entry.shiniesObtained;
            cached.shinyTargetCount = entry.shinyTargetCount;
            cached.missedShinies = entry.missedShinies;
            row.children[6].textContent = "";
            row.children[6].append(...renderCatchCount(entry.shiniesObtained, entry.shinyTargetCount, entry.missedShinies));
        }
    }
};

/**
 * @param {OverlayState} state
 * @param {StreamOverlay.SectionChecklist} checklistConfig
 */
const updateRouteEncountersList = (state, checklistConfig) => {
    const encounterList = getEncounterList(state);

    // Display a 'no encounters on this map' message if no encounters exist at all.
    if (encounterList.length === 0) {
        noEncountersMessage.style.display = "block";
        table.style.display = "none";

        while (cachedRouteEncountersList.length > 0) {
            const row = cachedRouteEncountersList.pop();
            row.element.remove();
        }

        return;
    } else if (cachedRouteEncountersList.length === 0) {
        noEncountersMessage.style.display = "none";
        table.style.display = "table";
    }

    let numberOfAntis = 0;
    let numberOfPossibleEncounters = 0;

    /** @type {Object.<string, RouteEncounterEntry>} routeEncounters */
    const routeEncounters = {};
    for (const encounter of encounterList) {
        const species = state.stats.pokemon[encounter.species_name] ?? getEmptySpeciesEntry(encounter.species_id, encounter.species_name);
        const currentPhase = state.stats.current_phase;

        let isAnti = false;
        if (species && species.phase_highest_sv > 65527) {
            isAnti = true;
            numberOfAntis++;
        }

        if (encounter.encounter_rate > 0) {
            numberOfPossibleEncounters++;
        } else if (numberOfAntis === numberOfPossibleEncounters) {
            // Show the entire list (including encounters that are dropped due to Repel) as
            // anti-shiny if all possible encounters have been encountered as an anti already.
            isAnti = true;
        }

        routeEncounters[encounter.species_name] = {
            element: null,
            spriteElement: null,
            speciesName: encounter.species_name,
            isAnti: isAnti,
            encounterRate: encounter.encounter_rate,
            highestSV: species?.phase_highest_sv,
            lowestSV: species?.phase_lowest_sv,
            highestIVSum: species?.phase_highest_iv_sum,
            lowestIVSum: species?.phase_lowest_iv_sum,
            phaseEncounters: species?.phase_encounters ?? 0,
            phaseEncounterShare: species ? species.phase_encounters / currentPhase.encounters : null,
            totalEncounters: species?.total_encounters ?? 0,
            shinyRateDivisor: species ? Math.round(species.total_encounters / species.shiny_encounters) : null,
            shiniesObtained: species?.catches ?? 0,
            shinyTargetCount: getSpeciesGoal(encounter.species_name, checklistConfig),
            missedShinies: (species?.shiny_encounters ?? 0) - (species?.catches ?? 0),
        };
    }

    for (const entry of Object.values(routeEncounters)) {
        const speciesCatches = getSpeciesCatches(entry.speciesName, checklistConfig, state.stats, Object.keys(routeEncounters));
        if (entry.shiniesObtained < entry.shinyTargetCount) {
            entry.shinyTargetCount -= Math.min(speciesCatches - entry.shiniesObtained, entry.shinyTargetCount - 1);
        }

        if (!ALTERNATIVE_SPECIES.hasOwnProperty(entry.speciesName)) {
            continue;
        }

        for (const alternativeSpeciesName of ALTERNATIVE_SPECIES[entry.speciesName]) {
            if (!routeEncounters.hasOwnProperty(alternativeSpeciesName)) {
                if (state.stats.pokemon.hasOwnProperty(alternativeSpeciesName)) {
                    const alternativeSpecies = state.stats.pokemon[alternativeSpeciesName];
                    if (alternativeSpecies.catches > 1) {
                        entry.shinyTargetCount -= Math.max(0, Math.min(entry.shinyTargetCount, alternativeSpecies.catches - 1));
                    }
                }
                continue;
            }

            const alternative = routeEncounters[alternativeSpeciesName];
            if (entry.shinyTargetCount > 0) {
                entry.shinyTargetCount--;
                alternative.shinyTargetCount -= entry.shinyTargetCount;
            }

            if (entry.shinyTargetCount > 0 && entry.shiniesObtained < entry.shinyTargetCount) {
                let alternativeExcess = alternative.shiniesObtained - alternative.shinyTargetCount;
                while (alternativeExcess > 0 && entry.shinyTargetCount > entry.shiniesObtained) {
                    alternativeExcess--;
                    alternative.shinyTargetCount++;
                    entry.shinyTargetCount--;
                }
            }
        }
    }

    renderRouteEncountersList(Object.values(routeEncounters));

    if (cachedAntiShinyCount !== state.stats.current_phase.anti_shiny_encounters) {
        cachedAntiShinyCount = state.stats.current_phase.anti_shiny_encounters;
        antiShinyCounter.textContent = "";
        if (cachedAntiShinyCount > 0) {
            const sparkles = [];
            for (let index = 0; index < cachedAntiShinyCount; index++) {
                const img = document.createElement("img");
                img.src = "/static/sprites/stream-overlay/anti-shiny.png";
                img.alt = "";
                sparkles.push(img);
            }
            antiShinyCounter.append(...sparkles);
        }
    }
}

export {updateMapName, animateRouteEncounterSprite, updateRouteEncountersList};
