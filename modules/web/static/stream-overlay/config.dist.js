// 'Temporary' thing for Cakes: Just change this to the next number
// whenever a section is completed.
//    4 = before badges 4 and 5 (desert and fossil)
//    5 = before Mind Badge (first Safari Zone etc.)
//    6 = before Rain Badge (the one with the Regis and Rayquaza)
//    7 = before Feather Badge (Mawile and Bagon)
//    8 = post E4
//    9 = Event Pokémon
const section = 4;


/** @type {StreamOverlay.Config} config */
const config = {

    // These settings are being used for the time widget in the
    // top left corner.
    startDate: "2023-01-01",
    timeZone: "Australia/Sydney",
    overrideDisplayTimezone: "AEST",

    // Number of individual shiny species required to complete the
    // challenge.
    totalShinySpeciesTarget: 212,

    // A list of species names (can be empty) that a timer since
    // the last encounter should be displayed for in the bottom
    // right corner of the game video.
    targetTimers: ["Cacnea"],

    // How long the encounter stats (values in the top right
    // corner) should be visible for hatched eggs and gift
    // Pokémon. (For battle encounters, the stats disappear
    // after the battle ended.)
    // In seconds.
    nonBattleEncounterStatsTimeoutInSeconds: 15,

    // If we receive a PokéNav call, count them (per phase) and
    // display the counter as an info bubble.
    showPokeNavCallCounter: false,

    // Display the info bubble that shows the number of Pokémon
    // in the PC storage system.
    showPCStorageCounter: false,

    // An ISO date string (e.g. `2025-01-01T12:34:56` or a UNIX
    // timestamp (in seconds or ms.) If set, the overlay will
    // display an info bubble counting down to that moment in
    // time.
    countdownTarget: null,

    // These can be used to hardcode the longest phase in case
    // this data is incorrect in the stats database.
    overrideLongestPhase: {
        species_name: "Lotad",
        value: 62686,
    },

    overrideShortestPhase: {
        species_name: "Wurmple",
        value: 7,
    },

    // List of required shiny Pokémon for the current section.
    //
    // It is possible to group multiple species in one entry by
    // adding the aliases to the `similarSpecies` list. If this
    // is set, any shiny for any of the species will be counted
    // towards that entry's goal.
    //
    // Setting the `hidden` property to `true` means that the
    // entry will be used for calculating the progress bar, but
    // it will not show up in the checklist widget.
    sectionChecklist: {
        4: {
            "Sandshrew": {
                goal: 2,
                similarSpecies: ["Sandslash"],
                hidden: false,
            },

            "Trapinch": {
                goal: 3,
                similarSpecies: ["Vibrava", "Flygon"],
                hidden: false,
            },

            "Cacnea": {
                goal: 2,
                similarSpecies: ["Cacturne"],
                hidden: false,
            },

            "Baltoy": {
                goal: 2,
                similarSpecies: ["Claydol"],
                hidden: false,
            },

            "Anorith": {
                goal: 2,
                similarSpecies: ["Armaldo"],
                hidden: false,
            },
        },

        5: {
            "Jigglypuff": {
                goal: 1,
                similarSpecies: ["Wigglytuff"],
                hidden: false,
            },

            "Magnemite": {
                goal: 2,
                similarSpecies: ["Magneton"],
                hidden: false,
            },

            "Voltorb": {
                goal: 2,
                similarSpecies: ["Electrode"],
                hidden: false,
            },

            "Horsea": {
                goal: 2,
                similarSpecies: ["Seadra", "Kingdra"],
                hidden: false,
            },

            "Staryu": {
                goal: 1,
                similarSpecies: ["Starmie"],
                hidden: false,
            },

            "Corsola": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Carvanha": {
                goal: 2,
                similarSpecies: ["Sharpedo"],
                hidden: false,
            },

            "Wailmer": {
                goal: 2,
                similarSpecies: ["Wailord"],
                hidden: false,
            },

            "Barboach": {
                goal: 2,
                similarSpecies: ["Whiscash"],
                hidden: false,
            },

            "Corphish": {
                goal: 2,
                similarSpecies: ["Crawdaunt"],
                hidden: false,
            },

            "Feebas": {
                goal: 2,
                similarSpecies: ["Milotic"],
                hidden: false,
            },

            "Luvdisc": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Castform": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Tropius": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Absol": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Shuppet": {
                goal: 2,
                similarSpecies: ["Banette"],
                hidden: false,
            },

            "Duskull": {
                goal: 2,
                similarSpecies: ["Dusclops"],
                hidden: false,
            },

            "Vulpix": {
                goal: 2,
                similarSpecies: ["Ninetales"],
                hidden: false,
            },

            "Chimecho": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Pikachu": {
                goal: 2,
                similarSpecies: ["Raichu"],
                hidden: false,
            },

            "Psyduck": {
                goal: 2,
                similarSpecies: ["Golduck"],
                hidden: false,
            },

            "Doduo": {
                goal: 2,
                similarSpecies: ["Dodrio"],
                hidden: false,
            },

            "Rhyhorn": {
                goal: 2,
                similarSpecies: ["Rhydon"],
                hidden: false,
            },

            "Pinsir": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Natu": {
                goal: 2,
                similarSpecies: ["Xatu"],
                hidden: false,
            },

            "Girafarig": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Heracross": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Phanpy": {
                goal: 2,
                similarSpecies: ["Donphan"],
                hidden: false,
            },

            "Snorunt": {
                goal: 2,
                similarSpecies: ["Glalie"],
                hidden: false,
            },

            "Spheal": {
                goal: 3,
                similarSpecies: ["Sealeo", "Walrein"],
                hidden: false,
            },

            "Pichu": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Igglybuff": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Azurill": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Wynaut": {
                goal: 2,
                similarSpecies: ["Wobbuffet"],
                hidden: false,
            },

            "Kecleon": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Vileplume": {
                goal: 3,
                similarSpecies: ["Oddish", "Gloom"],
                hidden: false,
            },
        },

        6: {
            "Chinchou": {
                goal: 2,
                similarSpecies: ["Lanturn"],
                hidden: false,
            },

            "Clamperl": {
                goal: 1,
                similarSpecies: ["Huntail", "Gorebyss"],
                hidden: false,
            },

            "Relicanth": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Regirock": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Regice": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Registeel": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Rayquaza": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Shiftry": {
                goal: 3,
                similarSpecies: ["Seedot", "Nuzleaf"],
                hidden: false,
            },

            "Starmie": {
                goal: 2,
                similarSpecies: ["Staryu"],
                hidden: false,
            },

            "Ludicolo": {
                goal: 3,
                similarSpecies: ["Lotad", "Lombre"],
                hidden: false,
            },
        },

        7: {
            "Mawile": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Bagon": {
                goal: 3,
                similarSpecies: ["Shelgon", "Salamence"],
                hidden: false,
            },
        },

        8: {
            "Latias": {
                goal: 1,
                similarSpecies: ["Latios"],
                hidden: false,
            },

            "Lileep": {
                goal: 2,
                similarSpecies: ["Cradily"],
                hidden: false,
            },

            "Beldum": {
                goal: 3,
                similarSpecies: ["Metang", "Metagross"],
                hidden: false,
            },

            "Kyogre": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Groudon": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Ditto": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Sudowoodo": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Smeargle": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Hoothoot": {
                goal: 2,
                similarSpecies: ["Noctowl"],
                hidden: false,
            },

            "Ledyba": {
                goal: 2,
                similarSpecies: ["Ledian"],
                hidden: false,
            },

            "Spinarak": {
                goal: 2,
                similarSpecies: ["Ariados"],
                hidden: false,
            },

            "Mareep": {
                goal: 3,
                similarSpecies: ["Flaaffy", "Ampharos"],
                hidden: false,
            },

            "Aipom": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Sunkern": {
                goal: 2,
                similarSpecies: ["Sunflora"],
                hidden: false,
            },

            "Wooper": {
                goal: 2,
                similarSpecies: ["Quagsire"],
                hidden: false,
            },

            "Pineco": {
                goal: 2,
                similarSpecies: ["Forretress"],
                hidden: false,
            },

            "Gligar": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Snubbull": {
                goal: 2,
                similarSpecies: ["Granbull"],
                hidden: false,
            },

            "Shuckle": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Teddiursa": {
                goal: 1,
                similarSpecies: ["Ursaring"],
                hidden: false,
            },

            "Remoraid": {
                goal: 2,
                similarSpecies: ["Octillery"],
                hidden: false,
            },

            "Houndour": {
                goal: 2,
                similarSpecies: ["Houndoom"],
                hidden: false,
            },

            "Stantler": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Miltank": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Meowth": {
                goal: 2,
                similarSpecies: ["Persian"],
                hidden: false,
            },

            "Mudkip": {
                goal: 3,
                similarSpecies: ["Mashtomp", "Swampert"],
                hidden: false,
            },
        },

        9: {
            "Mew": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Lugia": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Ho-Oh": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Latios": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },

            "Deoxys": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },
        }
    }[section],

};

export default config;
