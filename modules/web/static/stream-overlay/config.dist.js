// 'Temporary' thing for Cakes: Just change this to `true` after
// the desert and fossil section has been completed.
const isSectionSix = false;


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
    sectionChecklist: !isSectionSix
        ? {
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
        }

        : {
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
                similarSpecies: [],
                hidden: false,
            },

            "Kecleon": {
                goal: 1,
                similarSpecies: [],
                hidden: false,
            },
        }

};

export default config;
