import {ItemBag, ItemStorage, MapLocation, Player, PlayerAvatarType, Pokedex, Pokemon, PokemonStorage} from "./pokemon";
import {EffectiveEncounterList, Encounter, GlobalStats, RegularEncounterList, ShinyPhase} from "./stats";

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
     * Response body for `GET /game_state`
     */
    export type GetGameStateResponse = string;

    /**
     * Response body for `GET /player`.
     */
    export type GetPlayerResponse = null | Player;

    /**
     * Response body for `GET /player_avatar`
     */
    export type GetPlayerAvatarResponse = null | PlayerAvatarType;

    /**
     * Response body for `GET /pokedex`
     */
    export type GetPokedexResponse = Pokedex;

    /**
     * Response body for `GET /party`.
     */
    export type GetPartyResponse = Pokemon[];

    /**
     * Response body for `GET /opponent`.
     */
    export type GetOpponentResponse = Pokemon | null;

    /**
     * Response body for `GET /pokemon_storage`.
     */
    export type GetPokemonStorageResponse = PokemonStorage;

    /**
     * Response body for `GET /pokemon_storage?format=size-only`.
     */
    export type GetPokemonStorageSizeResponse = {
        pokemon_stored: number;
        boxes: number[];
    };

    /**
     * Response body for `GET /daycare`.
     */
    export type GetDaycareResponse = {
        pokemon1: Pokemon;
        pokemon1_steps: number;
        pokemon1_new_level: number;

        pokemon2: Pokemon;
        pokemon2_steps: number;
        pokemon2_new_level: number;

        compatibility: string;
        compatibility_explanation: string;

        step_counter: number;
    }

    /**
     * Response body for `GET /items`.
     */
    export type GetItemsResponse = {
        // Items that the player is carrying.
        bag: ItemBag;

        // Items that are stored in the PC.
        storage: ItemStorage;
    };

    /**
     * Response body for `GET /map`.
     */
    export type GetMapResponse = MapLocation;

    /**
     * Response body for `GET /map_encounters`.
     */
    export type GetMapEncountersResponse = {
        repel_level: number;
        active_ability: string | null;
        active_items: string[];
        regular: RegularEncounterList;
        effective: EffectiveEncounterList;
    };

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

    /**
     * Response body for `GET /encounter_log`.
     */
    export type GetEncounterLogResponse = Encounter[];

    /**
     * Response body for `GET /shiny_log`.
     */
    export type GetShinyLogResponse = ShinyPhase[];

    /**
     * Response body for `GET /stats`.
     */
    export type GetStatsResponse = GlobalStats;
}
