import {Pokemon} from "./pokemon";

export type EncounterSummary = {
    species_id: number | null;
    species_name: string | null;
    total_encounters: number;
    shiny_encounters: number;
    catches: number;
    total_highest_iv_sum: number;
    total_lowest_iv_sum: number;
    total_highest_sv: number;
    total_lowest_sv: number;
    phase_encounters: number;
    phase_highest_iv_sum: number | null;
    phase_lowest_iv_sum: number | null;
    phase_highest_sv: number | null;
    phase_lowest_sv: number | null;
    last_encounter_time: string;
};


export type EncounterTotals = {
    total_encounters: number;
    shiny_encounters: number;
    catches: number;
    total_highest_iv_sum: SpeciesRecord;
    total_lowest_iv_sum: SpeciesRecord;
    total_highest_sv: SpeciesRecord;
    total_lowest_sv: SpeciesRecord;

    phase_encounters: number;
    phase_highest_iv_sum: SpeciesRecord;
    phase_lowest_iv_sum: SpeciesRecord;
    phase_highest_sv: SpeciesRecord;
    phase_lowest_sv: SpeciesRecord;
};


type SpeciesRecord = {
    value: number;
    species_name: string | null;
}

export enum EncounterType {
    Trainer = "trainer",
    Roamer = "roamer",
    Static = "static",
    Land = "land",
    Surfing = "surfing",
    FishingWithOldRod = "fishing_old_rod",
    FishingWithGoodRod = "fishing_good_rod",
    FishingWithSuperRod = "fishing_super_rod",
    RockSmash = "rock_smash",
}

type BattleOutcome =
    | "InProgress"
    | "Won"
    | "Lost"
    | "Draw"
    | "RanAway"
    | "PlayerTeleported"
    | "OpponentFled"
    | "Caught"
    | "NoSafariBallsLeft"
    | "Forfeited"
    | "OpponentTeleported"
    | "LinkBattleRanAway";


export type Encounter = {
    encounter_id: number;
    shiny_phase_id: number;
    matching_custom_catch_filters: string | null;
    encounter_time: string;
    map: string | null;
    coordinates: string | null;
    bot_mode: string;
    type: EncounterType | null;
    outcome: BattleOutcome | null;
    pokemon: Pokemon;
};


export type ShinyPhase = {
    phase: {
        shiny_phase_id: number;
        start_time: string;
        end_time: string | null;
        encounters: number;
        highest_iv_sum: SpeciesRecord;
        lowest_iv_sum: SpeciesRecord;
        highest_sv: SpeciesRecord;
        lowest_sv: SpeciesRecord;
        longest_streak: SpeciesRecord;
        current_streak: SpeciesRecord;
        fishing_attempts: number;
        successful_fishing_attempts: number;
        longest_unsuccessful_fishing_streak: number;
        current_unsuccessful_fishing_streak: number;
    };
    snapshot: {
        total_encounters: number;
        total_shiny_encounters: number;
        species_encounters: number;
        species_shiny_encounters: number;
    };
    shiny_encounter: Encounter | null;
};


export type GlobalStats = {
    pokemon: { [k: string]: EncounterSummary; };
    totals: EncounterTotals;
    current_phase: {
        start_time: string;
        encounters: number;
        highest_iv_sum: SpeciesRecord;
        lowest_iv_sum: SpeciesRecord;
        highest_sv: SpeciesRecord;
        lowest_sv: SpeciesRecord;
        longest_streak: SpeciesRecord;
        current_streak: SpeciesRecord;
        fishing_attempts: number;
        successful_fishing_attempts: number;
        longest_unsuccessful_fishing_streak: number;
        current_unsuccessful_fishing_streak: number;
    };
    longest_phase: SpeciesRecord;
    shortest_phase: SpeciesRecord;
    pickup_items: { [k: string]: number; };
};


export type MapEncounter = {
    species_id: number;
    species_name: string;
    min_level: number;
    max_level: number;
    encounter_rate: string;
};


export type RegularEncounterList = {
    land_encounter_rate: number
    surf_encounter_rate: number
    rock_smash_encounter_rate: number
    fishing_encounter_rate: number

    land_encounters: MapEncounter[];
    surf_encounters: MapEncounter[];
    rock_smash_encounters: MapEncounter[];
    old_rod_encounters: MapEncounter[];
    good_rod_encounters: MapEncounter[];
    super_rod_encounters: MapEncounter[];
}

export type EffectiveEncounterList = {
    land_encounters: MapEncounter[];
    surf_encounters: MapEncounter[];
    rock_smash_encounters: MapEncounter[];
    old_rod_encounters: MapEncounter[];
    good_rod_encounters: MapEncounter[];
    super_rod_encounters: MapEncounter[];
}
