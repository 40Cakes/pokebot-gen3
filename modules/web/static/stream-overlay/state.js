import config from "./config.js";

export const WILD_ENCOUNTER_TYPES = [
    "land",
    "surfing",
    "fishing_old_rod",
    "fishing_good_rod",
    "fishing_super_rod",
    "rock_smash"
];

const ENCOUNTER_LOG_LENGTH = 8;

export default class OverlayState {
    /** @type {GlobalStats} */
    stats = {
        pokemon: {},
        totals: {
            total_encounters: 0,
            shiny_encounters: 0,
            catches: 0,
            total_highest_iv_sum: null,
            total_lowest_iv_sum: null,
            total_highest_sv: null,
            total_lowest_sv: null,
            phase_encounters: 0,
            phase_highest_iv_sum: null,
            phase_lowest_iv_sum: null,
            phase_highest_sv: null,
            phase_lowest_sv: null,
        },
        current_phase: {
            start_time: 0,
            encounters: 0,
            highest_iv_sum: null,
            lowest_iv_sum: null,
            highest_sv: null,
            lowest_sv: null,
            longest_streak: null,
            current_streak: null,
            fishing_attempts: 0,
            successful_fishing_attempts: 0,
            longest_unsuccessful_fishing_streak: 0,
            current_unsuccessful_fishing_streak: 0,
            pokenav_calls: 0,
        },
        longest_phase: null,
        shortest_phase: null,
        pickup_items: {},
    };

    /** @type {MapLocation|null} */
    map = null;

    /** @type {PokeBotApi.GetMapEncountersResponse|null} */
    mapEncounters = null;

    /** @type {ShinyPhase[]} */
    shinyLog = [];

    /** @type {Encounter[]} */
    encounterLog = [];

    /** @type {PlayerAvatarType|null} */
    playerAvatar = null;

    /** @type {Pokemon[]} */
    party = [];

    /** @type {PokeBotApi.GetEmulatorResponse} */
    emulator = {
        emulation_speed: 1,
        video_enabled: true,
        audio_enabled: true,
        bot_mode: "Manual",
        current_message: "",
        frame_count: 0,
        current_fps: 0,
        current_time_spent_in_bot_fraction: 0,
        profile: {name: ""},
        game: null,
    };

    /** @type {PokeBotApi.GetEventFlagsResponse} */
    eventFlags = {};

    /** @type {number} */
    encounterRate = 0;

    /** @type {string} */
    gameState = "UNKNOWN";

    /** @type {PokemonStorage} */
    pokemonStorage = {
        active_box_index: 0,
        pokemon_count: 0,
        boxes: [],
    };

    /** @type {PokeBotApi.GetDaycareResponse} */
    daycare = {
        pokemon1: null,
        pokemon1_steps: 0,
        pokemon2: null,
        pokemon2_steps: 0,
        compatibility: "",
        compatibility_explanation: "",
        step_counter: 0,
    };

    /** @type {boolean} */
    daycareMode = false;

    /** @type {number | null} */
    countdownTarget = config.countdownTarget ?? null;

    /** @type {Set<string>} */
    additionalTargetTimers = new Set();

    /** @type {Set<string>} */
    additionalRouteSpecies = new Set();

    /** @type {"Old" | "Good" | "Super"} */
    lastFishingRod = "Old";

    /** @type {string|null} */
    #cachedLastEncounterType = null;

    /** @type {Encounter|null} */
    #cachedLastEncounter = null;

    reset() {
        this.additionalRouteSpecies.clear();
        this.#cachedLastEncounterType = null;
        this.#cachedLastEncounter = null;

        if (this.lastEncounter && ["hatched", "gift", "static"].includes(this.lastEncounter.type)) {
            this.additionalRouteSpecies.add(this.lastEncounter.pokemon.species_name_for_stats);
        }
    }

    /** @returns {string[]} */
    get targetTimers() {
        const timers = new Set();
        for (const speciesName of config.targetTimers) {
            timers.add(speciesName);
        }
        for (const speciesName of this.additionalTargetTimers) {
            timers.add(speciesName);
        }
        return [...timers];
    }

    /** @return {Encounter|null} */
    get lastEncounter() {
        if (this.#cachedLastEncounter) {
            return this.#cachedLastEncounter;
        } else if (this.encounterLog.length > 0) {
            this.#cachedLastEncounter = this.encounterLog[0];
            return this.encounterLog[0];
        } else {
            return null;
        }
    }

    get lastEncounterType() {
        if (this.#cachedLastEncounterType === null) {
            if (this.lastEncounter === null || this.gameState === "MAIN_MENU" || this.gameState === "TITLE_SCREEN") {
                return "land";
            }

            this.additionalRouteSpecies.clear();

            if (WILD_ENCOUNTER_TYPES.includes(this.lastEncounter.type)) {
                this.#cachedLastEncounterType = this.lastEncounter.type;
            } else if (["hatched", "gift", "static"].includes(this.lastEncounter.type)) {
                this.additionalRouteSpecies.add(this.lastEncounter.pokemon.species_name_for_stats)
                this.#cachedLastEncounterType = this.lastEncounter.type;
            }

            if (this.#cachedLastEncounterType === "land" && this.playerAvatar && this.playerAvatar.flags.Surfing) {
                this.#cachedLastEncounterType = "surfing";
            } else if (this.#cachedLastEncounterType === "surfing" && this.playerAvatar && !this.playerAvatar.flags.Surfing) {
                this.#cachedLastEncounterType = "land";
            }
        }

        return this.#cachedLastEncounterType;
    }

    /** @param {StreamEvents.WildEncounter} encounter */
    logEncounter(encounter) {
        this.#cachedLastEncounter = encounter;
        if (WILD_ENCOUNTER_TYPES.includes(encounter.type)) {
            this.#cachedLastEncounterType = encounter.type;
        }

        const speciesName = encounter.pokemon.species_name_for_stats;

        if (["hatched", "gift", "static"].includes(encounter.type)) {
            this.additionalRouteSpecies.add(speciesName);
        }

        this.encounterLog.unshift(encounter);
        while (this.encounterLog.length > ENCOUNTER_LOG_LENGTH) {
            this.encounterLog.pop();
        }

        const sv = encounter.pokemon.shiny_value;
        const ivSum =
            encounter.pokemon.ivs.hp +
            encounter.pokemon.ivs.attack +
            encounter.pokemon.ivs.defence +
            encounter.pokemon.ivs.special_attack +
            encounter.pokemon.ivs.special_defence +
            encounter.pokemon.ivs.speed;

        const updateStreak = (type, section, streak_name, species_name, value) => {
            let isNewRecord = false;
            if (type === "min" && value < this.stats[section][streak_name]?.value) {
                isNewRecord = true;
            } else if (type === "max" && value > this.stats[section][streak_name]?.value) {
                isNewRecord = true;
            }

            if (!this.stats[section][streak_name] || !this.stats[section][streak_name]?.species_name || isNewRecord) {
                this.stats[section][streak_name] = {species_name, value};
            }
        }

        this.stats.totals.total_encounters++;
        updateStreak("max", "totals", "total_highest_iv_sum", encounter.pokemon.species.name, ivSum);
        updateStreak("min", "totals", "total_lowest_iv_sum", encounter.pokemon.species.name, ivSum);
        updateStreak("max", "totals", "total_highest_sv", encounter.pokemon.species.name, sv);
        updateStreak("min", "totals", "total_lowest_isv", encounter.pokemon.species.name, sv);

        this.stats.totals.phase_encounters++;
        updateStreak("max", "totals", "phase_highest_iv_sum", encounter.pokemon.species.name, ivSum);
        updateStreak("min", "totals", "phase_lowest_iv_sum", encounter.pokemon.species.name, ivSum);
        updateStreak("max", "totals", "phase_highest_sv", encounter.pokemon.species.name, sv);
        updateStreak("min", "totals", "phase_lowest_isv", encounter.pokemon.species.name, sv);

        if (!this.stats.pokemon[speciesName]) {
            this.stats.pokemon[speciesName] = {
                species_id: encounter.pokemon.species.index,
                species_name: encounter.pokemon.species.name,
                total_encounters: 1,
                shiny_encounters: 0,
                catches: 0,
                total_highest_iv_sum: ivSum,
                total_lowest_iv_sum: ivSum,
                total_highest_sv: sv,
                total_lowest_sv: sv,
                phase_encounters: 1,
                phase_highest_iv_sum: ivSum,
                phase_lowest_iv_sum: ivSum,
                phase_highest_sv: sv,
                phase_lowest_sv: sv,
                last_encounter_time: new Date().toISOString(),
            };
        } else {
            this.stats.pokemon[speciesName].total_encounters++;
            this.stats.pokemon[speciesName].phase_encounters++;
            this.stats.pokemon[speciesName].last_encounter_time = new Date().toISOString();
            if (this.stats.pokemon[speciesName].total_highest_iv_sum < ivSum) {
                this.stats.pokemon[speciesName].total_highest_iv_sum = ivSum;
            }
            if (this.stats.pokemon[speciesName].total_lowest_iv_sum > ivSum) {
                this.stats.pokemon[speciesName].total_lowest_iv_sum = ivSum;
            }
            if (this.stats.pokemon[speciesName].total_highest_sv < sv) {
                this.stats.pokemon[speciesName].total_highest_sv = sv;
            }
            if (this.stats.pokemon[speciesName].total_lowest_sv > sv) {
                this.stats.pokemon[speciesName].total_lowest_sv = sv;
            }
            if (this.stats.pokemon[speciesName].phase_highest_iv_sum === null || this.stats.pokemon[speciesName].phase_highest_iv_sum < ivSum) {
                this.stats.pokemon[speciesName].phase_highest_iv_sum = ivSum;
            }
            if (this.stats.pokemon[speciesName].phase_lowest_iv_sum === null || this.stats.pokemon[speciesName].phase_lowest_iv_sum > ivSum) {
                this.stats.pokemon[speciesName].phase_lowest_iv_sum = ivSum;
            }
            if (this.stats.pokemon[speciesName].phase_highest_sv === null || this.stats.pokemon[speciesName].phase_highest_sv < sv) {
                this.stats.pokemon[speciesName].phase_highest_sv = sv;
            }
            if (this.stats.pokemon[speciesName].phase_lowest_sv === null || this.stats.pokemon[speciesName].phase_lowest_sv > sv) {
                this.stats.pokemon[speciesName].phase_lowest_sv = sv;
            }
        }

        this.stats.current_phase.encounters++;
        updateStreak("max", "current_phase", "highest_iv_sum", encounter.pokemon.species.name, ivSum);
        updateStreak("min", "current_phase", "lowest_iv_sum", encounter.pokemon.species.name, ivSum);
        updateStreak("max", "current_phase", "highest_sv", encounter.pokemon.species.name, sv);
        updateStreak("min", "current_phase", "lowest_sv", encounter.pokemon.species.name, sv);

        if (this.stats.current_phase?.current_streak?.species_name === encounter.pokemon.species.name) {
            this.stats.current_phase.current_streak.value++;
        } else {
            this.stats.current_phase.current_streak = {
                species_name: encounter.pokemon.species.name,
                value: 1,
            };
        }
        if (!this.stats.current_phase?.longest_streak?.species_name || this.stats.current_phase.longest_streak.value < this.stats.current_phase.current_streak.value) {
            this.stats.current_phase.longest_streak = {
                species_name: this.stats.current_phase.current_streak.species_name,
                value: this.stats.current_phase.current_streak.value,
            };
        }

        if (encounter.pokemon.is_shiny) {
            this.stats.totals.shiny_encounters++;
            // We don't do this because then the overlay would show '1 missed' during
            // the encounter (because `shiny_encounters` would be lower than `catches`.)
            // The stats are being reloaded from the bot after the encounter ends anyway.
            // this.stats.pokemon[speciesName].shiny_encounters++;

            if (["hatched", "gift", "static"].includes(encounter.type)) {
                this.stats.totals.catches++;
                this.stats.pokemon[speciesName].shiny_encounters++;
                this.stats.pokemon[speciesName].catches++;
            }

            for (const species in this.stats.pokemon) {
                this.stats.pokemon[species].phase_encounters = 0;
                this.stats.pokemon[species].phase_highest_iv_sum = null;
                this.stats.pokemon[species].phase_lowest_iv_sum = null;
                this.stats.pokemon[species].phase_encounters = null;
                this.stats.pokemon[species].phase_encounters = null;
            }
        }
    }

    /** @param {StreamEvents.FishingAttempt} attempt */
    logFishingAttempt(attempt) {
        this.stats.current_phase.fishing_attempts++;
        if (attempt.result === "Encounter") {
            this.stats.current_phase.successful_fishing_attempts++;
            this.stats.current_phase.current_unsuccessful_fishing_streak = 0;
        } else {
            this.stats.current_phase.current_unsuccessful_fishing_streak++;
            if (this.stats.current_phase.longest_unsuccessful_fishing_streak < this.stats.current_phase.current_unsuccessful_fishing_streak) {
                this.stats.current_phase.longest_unsuccessful_fishing_streak = this.stats.current_phase.current_unsuccessful_fishing_streak
            }
        }

        if (attempt.rod === "GoodRod") {
            this.lastFishingRod = "Good";
        } else if (attempt.rod === "SuperRod") {
            this.lastFishingRod = "Super";
        } else {
            this.lastFishingRod = "Old";
        }
    }

    logPokenavCall() {
        this.stats.current_phase.pokenav_calls++;
    }

    /** @param {StreamEvents.MapChange} map */
    logNewMap(map) {
        this.map = map.map;
        this.additionalRouteSpecies.clear();
        if (this.lastEncounter && ["hatched", "gift", "static"].includes(this.lastEncounter.type) && !this.additionalRouteSpecies.has(this.lastEncounter.pokemon.species_name_for_stats)) {
            this.additionalRouteSpecies.add(this.lastEncounter.pokemon.species_name_for_stats);
        }
    }

    /**
     * @param {StreamEvents.PlayerAvatar} data
     * @return {boolean} If the last encounter type has changed.
     * */
    logPlayerAvatarChange(data) {
        this.playerAvatar = data;
        if (this.lastEncounterType === "land" && data.flags.Surfing) {
            this.#cachedLastEncounterType = "surfing";
            return true;
        } else if (this.lastEncounterType === "surfing" && !data.flags.Surfing) {
            this.#cachedLastEncounterType = "land";
            return true;
        }
        return false;
    }
}
