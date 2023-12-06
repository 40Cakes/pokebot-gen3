import {MapLocation, Pokedex as PokedexType, Pokemon} from "./pokemon";

declare module StreamEvents {
    export type PerformanceData = {
        // Most recently recorded FPS value (usually within the last second.)
        fps: number;

        // Number of frames that have been emulated since 'turning on' the virtual GBA.
        // This does not reset after restarting the bot since we are using save states,
        // so from the perspective of the game the GBA has been on the entire time.
        frame_count: number;

        // Value between 0 and 1, indicating how much of processing time has been used
        // by the bot itself as opposed to the GBA emulation. This is not an indicator
        // of how fast the bot is running in general.
        current_time_spent_in_bot_fraction: number;

        // Last calculated encounter rate.
        encounter_rate: number;
    };

    // Lists Pokémon in the current party. May contain between 0 and 6 entries.
    export type Party = Pokemon[];

    // Lists of seen/owned species.
    export type Pokedex = PokedexType;

    // Contains data about the Pokémon that is currently being battled against, or NULL
    // if there is no active battle.
    export type Opponent = Pokemon | null;

    export type MapChange = MapLocation;

    // New x and y coordinates of the player position.
    export type MapTileChange = [number, number];

    export type Message = string;

    export type GameState = string;

    export type BotMode = string;

    // 0 for unthrottled, otherwise the speed multiplier.
    export type EmulationSpeed = 0 | 1 | 2 | 3 | 4;

    export type AudioEnabled = boolean;

    export type VideoEnabled = boolean;
}
