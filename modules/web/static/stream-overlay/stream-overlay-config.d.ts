declare namespace StreamOverlay {

    export type SectionChecklist = {
        [k: string]: {
            goal: number;
            similarSpecies?: string[];
            hidden?: boolean;
        }
    };

    export type Config = {
        startDate: string;
        timeZone?: string | null;
        overrideDisplayTimezone?: string | null;

        totalShinySpeciesTarget: number;

        targetTimers: string[];

        nonBattleEncounterStatsTimeoutInSeconds: number;

        showPokeNavCallCounter: boolean;
        showPCStorageCounter: boolean;

        overrideLongestPhase?: {
            species_name: string;
            value: number;
        } | null;

        overrideShortestPhase: {
            species_name: string;
            value: number;
        } | null;

        sectionChecklist: SectionChecklist;
    };

}
