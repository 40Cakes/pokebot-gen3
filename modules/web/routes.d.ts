import {MapLocation, Pokemon} from "./pokemon";

declare module PokeBotApi {
    /**
     * Request body for `POST /emulator`
     *
     * The request must have `Content-Type: application/json`.
     * The response for this request is `GetEmulatorResponse` (same
     * as the one for `GET /emulator`.)
     */
    export type PostEmulatorRequest = {
        // 0 = unthrottled, other values are speed multipliers.
        emulation_speed?: 0 | 1 | 2 | 3 | 4;
        bot_mode?: string;
        video_enabled?: boolean;
        audio_enabled?: boolean;
    };

    /**
     * Response body for `GET /emulator` and `POST /emulator`.
     */
    export type GetEmulatorResponse = {
        // 0 = unthrottled, other values are speed multipliers.
        emulation_speed: 0 | 1 | 2 | 3 | 4;

        video_enabled: boolean;
        audio_enabled: boolean;

        bot_mode: string;

        // Message that is displayed in the GUI.
        current_message: string;

        // Number of frames since 'starting' the GBA (this will not reset
        // when closing the bot because it is persisted in the save state,
        // so from the perspective of the game the GBA was never turned
        // off.)
        frame_count: number;

        current_fps: number;

        // Value between 0 and 1, indicating how much time per frame has
        // been spent in bot-related code (checking memory, deciding
        // what buttons to press...) as opposed to the actual GBA
        // emulation.
        current_time_spent_in_bot_fraction: number;

        // Currently running profile.
        profile: { name: string; };

        // Currently running game.
        game: {
            // In-ROM code for this game.
            title: "POKEMON RUBY" | "POKEMON SAPP" | "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF";

            // 'Version number' for this game, usually 0 or 1.
            revision: number;

            // More readable name of this game.
            name: string;

            // Game language.
            // E = English; F = French; D = German; I = Italian; J = Japanese;
            // S = Spanish.
            language: "E" | "F" | "D" | "I" | "J" | "S";
        }
    };

    /**
     * Response body for `GET /fps`.
     *
     * This endpoint lists FPS values over time. The array index is equivalent
     * to how many seconds ago that FPS value has been recorded.
     */
    export type GetFPSResponse = number[];

    /**
     * Response body for `GET /trainer`.
     */
    export type GetTrainerResponse = {
        name: string;
        gender: "boy" | "girl";

        // Trainer ID.
        tid: number;

        // Secret ID.
        sid: number;

        // Current map group and map number.
        map: [number, number];

        // Name of the map the player is currently on.
        map_name: string;

        // Local coordinates (in tiles) on the current map.
        coords: [number, number];

        running_state: number;
        tile_transition_state: number;
        acro_bike_state: number;
        on_bike: boolean;
        facing_direction: "Down" | "Up" | "Left" | "Right";

        game_state: string;
    };

    /**
     * Response body for `GET /party`.
     */
    export type GetPartyResponse = Pokemon[];

    /**
     * Response body for `GET /opponent`.
     */
    export type GetOpponentResponse = Pokemon | null;

    /**
     * Response body for `GET /items`.
     *
     * There is a key for each bag pocket, and within each of those there is an object
     * where the key is the name of an item and the value is the amount of said item.
     */
    export type GetItemsResponse = {
        "PC": { [k: string]: number };
        "Items": { [k: string]: number };
        "Key Items": { [k: string]: number };
        "Poké Balls": { [k: string]: number };
        "TMs & HMs": { [k: string]: number };
        "Berries": { [k: string]: number };
    };

    /**
     * Response body for `GET /map`.
     */
    export type GetMapResponse = MapLocation;

    /**
     * Response body for `GET /encounter_rate`.
     */
    export type GetEncounterRateResponse = {
        // Calculated average encounters per hour.
        encounter_rate: number;
    }

    /**
     * Respone body for `GET /event_flags`.
     */
    export type GetEventFlagsResponse = { [k: string]: number }
}
