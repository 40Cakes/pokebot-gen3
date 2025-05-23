declare namespace StreamOverlay {

    export type Config = {
        startDate: string;
        timeZone?: string | null;
        overrideDisplayTimezone?: string | null;

        targetTimers: string[];

        nonBattleEncounterStatsTimeoutInSeconds: number;

        overrideLongestPhase?: {
            species_name: string;
            value: number;
        } | null;

        overrideShortestPhase: {
            species_name: string;
            value: number;
        } | null;

        speciesChecklist: {
            [k: string]: {
                goal: number;
                similarSpecies?: string[];
                hidden?: boolean;
            }
        };
    };

}
