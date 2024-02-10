type Gender = "male" | "female";
type Language = "Japanese" | "English" | "French" | "Italian" | "German" | "Spanish";
type GameName = "Ruby" | "Sapphire" | "Emerald" | "FireRed" | "LeafGreen" | "Colosseum/XD" | "?";
type StatusCondition = "Healthy" | "Sleep" | "Poison" | "Burn" | "Freeze" | "Paralysis" | "BadPoison";
type Marking = "Circle" | "Square" | "Triangle" | "Heart";
type LevelUpType = "Medium Fast" | "Erratic" | "Fluctuating" | "Medium Slow" | "Fast" | "Slow";
type TypeName =
    "Normal"
    | "Fighting"
    | "Flying"
    | "Poison"
    | "Ground"
    | "Rock"
    | "Bug"
    | "Ghost"
    | "Steel"
    | "???"
    | "Fire"
    | "Water"
    | "Grass"
    | "Electric"
    | "Psychic"
    | "Ice"
    | "Dragon"
    | "Dark";
type ItemType =
    "Mail"
    | "UsableOutsideBattle"
    | "UsableInCertainLocations"
    | "PokeblockCase"
    | "NotUsableOutsideBattle";
type ItemPocket = "Items" | "PokeBalls" | "TmsAndHms" | "Berries" | "KeyItems";

type StatsValues = {
    hp: number;
    attack: number;
    defence: number;
    speed: number;
    special_attack: number;
    special_defence: number;
};

export type Type = {
    // Internal index number, not exposed anywhere in the game.
    index: number;

    // English name of this type.
    name: TypeName;

    kind: "???" | "Physical" | "Special";
}

export type Item = {
    // Internal index number, not exposed anywhere in the game.
    index: number;

    // English name of this item.
    name: string;

    // Buying price in the market.
    price: number;

    // Used for certain in-game checks, but not directly exposed to the player.
    type: ItemType;

    // Which bag pockets this item sorts into.
    pocket: ItemPocket;

    // An extra value whose meaning depends on the type of item.
    // For repels, it indicates the number of steps the effect lasts for; HP/PP
    // modifying items use it to indicate the number of HP/PP affected.
    parameter: number;

    // Used for mails and Poké Balls to indicate their type.
    extra_parameter: number;
};

export type Move = {
    // Internal index number, not exposed anywhere in the game.
    index: number;

    // English name of this move.
    name: string;

    type: Type;

    // Value between 0 and 1, indicating how likely it is for this
    // move to connect.
    accuracy: number;

    // Value between 0 and 1, indicating how likely it is for a
    // _secondary effect_ (such as optional status changes, etc.)
    // to connect.
    secondary_accuracy: number;

    pp: number;
    priority: number;
    base_power: number;

    // Internal name of the effect for this move.
    effect: string

    // Whom this move will hit in a double battle.
    target: "BOTH" | "DEPENDS" | "FOES_AND_ALLY" | "OPPONENTS_FIELD" | "RANDOM" | "SELECTED" | "USER";

    makes_contact: boolean;
    affected_by_protect: boolean;
    affected_by_magic_coat: boolean;
    affected_by_snatch: boolean;
    usable_with_mirror_move: boolean;
    affected_by_kings_rock: boolean;
};

export type LearnedMove = {
    move: Move;

    // Currently remaining number of PPs.
    pp: number;

    // Total PPs that this move can have.
    total_pp: number;

    // Amount of PPs that have been added by items for this Pokémon (this is the difference between `total_pp`
    // and the move's base PP value.)
    added_pps: number;
};

export type Ability = {
    // Internal index number, not exposed anywhere in the game.
    index: number;

    // English name of this ability.
    name: string;
};

export type Nature = {
    // Internal index number, not exposed anywhere in the game.
    index: number;

    // English name of this nature.
    name: string;

    // Indicates how this nature affects certain stats values. One of these values
    // could be `1.1` (to indicate a +10% modifier), one could be `0.9%` (for the -10%
    // modifier) and the rest will be `1`.
    modifiers: {
        attack: number;
        defence: number;
        speed: number;
        special_attack: number;
        special_defence: number;
    };
};

export type Species = {
    // Internal index number, not exposed anywhere in the game.
    index: number;

    national_dex_number: number;
    hoenn_dex_number: number;

    // English name of this species.
    name: string;

    // The species name with any characters that might be problematic in file names
    // replaced.
    safe_name: string;

    types: Type[];

    // List of abilities that this species can have.
    abilities: Ability[];

    // List of items that this Pokémon could hold when encountered in the wild.
    held_items: { item: Item; probability: number; }[];

    // The likelihood (between 0 and 254 that a Pokémon is female.
    // 0 = Pokémon is always male.
    // 254 = Pokémon is always female.
    // A special value means that this species is genderless/'Gender unknown'.
    gender_ratio: number;

    // Indicates how long it takes to hatch an egg of this species. (This value needs
    // to be multiplied by 256 to get an _approximate_ number of steps needed to hatch
    // it.)
    egg_cycles: number;

    base_stats: StatsValues;
    base_friendship: number;
    catch_rate: number;
    safari_zone_flee_probability: number;
    level_up_type: LevelUpType;
    egg_groups: string[];
    base_experience_yield: number;
    ev_yield: StatsValues;
};

export type Pokemon = {
    // Randomly generated value that does not do anything on its own, but from which
    // a lot of other values are being derived.
    personality_value: number;

    // This is the _effective_ name that is being displayed in-game.
    // For an egg, this will be `EGG`; for hatched Pokémon this will either be the
    // nickname (if one exists) or alternatively the species name.
    name: string;

    // The nickname that the player has chosen, or alternatively just the name of
    // the species (this is never empty.)
    nickname: string;

    // Language of the game that this Pokémon originates from.
    // For eggs, this is always "Japanese" and will be changed after hatching.
    language: Language;

    // Name of the game that this Pokémon originates from.
    game_of_origin: GameName;

    // Level at which this Pokémon has been caught. If this is 0, it means the Pokémon
    // has hatched from an egg.
    level_met: number;

    // Name of the in-game location that the Pokémon has been encountered/hatched at.
    // For Pokémon with an unrecognised location, this will be "Traded".
    location_met: string;

    // Information about this Pokémon's OT.
    original_trainer: {
        id: number;
        secret_id: number;
        name: string;
        gender: Gender;
    };

    is_egg: boolean;

    species: Species;

    held_item: Item | null;

    // Total number of Experience that this Pokémon has collected.
    total_exp: number;

    // Value between 0 and 255.
    friendship: number;

    ability: Ability;

    nature: Nature;

    // Gender of the Pokémon. For Pokémon species that do not have a gender (e.g.
    // Magnemite, Staryu, Ditto, Unown, ...) this is `null`.
    gender: Gender | null;

    // Current level of this Pokémon.
    level: number;

    // Number of EXP the Pokémon still needs to collect until the next level-up.
    // For level-100 Pokémon, this is always 0.
    exp_needed_until_next_level: number;

    // Number between 0 and 1, indicating how many EXP towards the next level have
    // already been collected.
    // For level-100 Pokémon, this is always 1.
    exp_fraction_to_next_level: number;

    // Current status condition of this Pokémon.
    status_condition: StatusCondition;

    // Turns remaining where this Pokémon will stay asleep.
    // Obviously, this is only relevant if `status_condition` is "Sleep".
    sleep_duration: number;

    // Current effective status values of this Pokémon, calculated from base stats,
    // level, EVs, IVs, and Nature.
    stats: StatsValues;

    // Total number of (max) HP that this Pokémon currently has.
    total_hp: number;

    // Current HP of this Pokémon (this is the value that decreases when the Pokémon
    // gets punched in the face.)
    current_hp: number;

    // Information about learned moves. The index of this array corresponds to the
    // move slot.
    moves: [LearnedMove | null, LearnedMove | null, LearnedMove | null, LearnedMove | null];

    evs: StatsValues;

    ivs: StatsValues;

    // Stats that are being used for the Pokémon Contest.
    contest_conditions: {
        coolness: number;
        beauty: number;
        cuteness: number;
        smartness: number;
        toughness: number;
        feel: number;
    };

    // The type of Poké Ball that this Pokémon has been caught in.
    poke_ball: Item;

    pokerus_status: {
        // This indicates the strain of Pokérus that a Pokémon has been infected
        // with. It is 0 for Pokémon that have never had Pokérus.
        strain: number;

        // Days remaining for the current infection. If this is 0 and `strain` is
        // anything other than 0, it means the Pokémon has been cured.
        days_remaining: number;
    };

    // Symbols that have been set for this Pokémon and which are shown in the
    // Summary Screen. They don't have any other in-game effect and are probably
    // just meant for easier organisation.
    markings: Marking[];

    // Value calculated from OT and Personality Value that is used for checking
    // whether a Pokémon is shiny or not. Not really useful on its own.
    shiny_value: number;

    // Whether this is a Shiny Pokémon.
    is_shiny: boolean;

    // Has no meaning for the game, just a mathematical curiosity.
    is_anti_shiny: boolean;

    hidden_power_type: Type;

    // Base damage of the Hidden Power move.
    hidden_power_damage: number;

    // If this Pokémon is a Unown, indicates what letter it is.
    unown_letter: string;

    // If this Pokémon is a Wurmple, indicates what it will evolve into.
    wurmple_evolution: "silcoon" | "cascoon";
};

export type Pokedex = {
    "seen": { "national_dex_number": number; name: string; }[];
    "owned": { "national_dex_number": number; name: string; }[];
};

export type MapType =
    "None"
    | "Town"
    | "City"
    | "Route"
    | "Underground"
    | "Underwater"
    | "Ocean Route"
    | "Unknown"
    | "Indoor"
    | "Secret Base";

export type Weather =
    "None"
    | "Sunny Clouds"
    | "Sunny"
    | "Rain"
    | "Snow"
    | "Thunderstorm"
    | "Fog (Horizontal)"
    | "Volcanic Ash"
    | "Sandstorm"
    | "Fog (Diagonal)"
    | "Underwater"
    | "Shade"
    | "Drought"
    | "Downpour"
    | "Underwater Bubbles"
    | "Abnormal"
    | "Route 119 Cycle"
    | "Route 123 Cycle"

type MapConnection = {
    direction: "South" | "North" | "West" | "East" | "Dive" | "Emerge";

    // Offset of the connecting map compared to this one, i.e. how many tiles
    // a player needs to be moved up/down/left/right (depending on connection
    // direction) when transitioning maps.
    offset: number;

    destination: {
        map_group: number;
        map_number: number;
        map_name: string;
    }
};

type MapWarp = {
    local_coordinates: [number, number];
    elevation: number;
    destination: {
        map_group: number;
        map_number: number;
        map_name: string;

        // Index of the warp on the destination map where this warp should
        // lead to. This is used to figure out the local coordinates at the
        // destination.
        warp_id: number;
    }
};

type MapTileEnterEvent = {
    local_coordinates: [number, number];
    elevation: number;

    // Name of the script symbol in the pret decompilation project.
    // This is not an official name and only here for easier reading of the list.
    script: string;
};

type MapTileInteractEvent =
    { local_coordinates: [number, number]; elevation: number; } & (
        | { kind: "Script"; player_facing_direction: "Any" | "Up" | "Down" | "Right" | "Left"; script: string; }
        | { kind: "Hidden Item"; item: string; }
        | { kind: "Secret Base"; secret_base_id: number; }
    );

type MapRegularObjectTemplate = {
    kind: "normal";

    local_id: number;
    local_coordinates: [number, number];
    elevation: number;

    // Name of the script symbol in the pret decompilation project.
    // This is not an official name and only here for easier reading of the list.
    script: string;

    trainer: { type: "None" | "Normal" | "See All Directions" | "Buried"; range: number; } | null;
    movement: { type: string; range: [number, number]; };
};

type MapCloneObjectTemplate = {
    kind: "clone";

    local_id: number;
    local_coordinates: [number, number];

    target: {
        "map_group": number;
        "map_number": number;
        "map_name": string;
        "local_id": number;
    }
};

type MapObjectTemplate = MapRegularObjectTemplate | MapCloneObjectTemplate;

type MapData = {
    map_group: number;
    map_number: number;

    // In-game name of the current map.
    name: string;

    // Size in tiles.
    size: [number, number];

    type: MapType;

    weather: Weather;

    is_cycling_possible: boolean;

    // Whether escape ropes can be used here.
    is_escaping_possible: boolean;

    is_running_possible: boolean;

    // Indicates whether the game will show a little pop-up with the map name
    // in the top-left corner when entering.
    is_map_name_popup_shown: boolean;

    // Indicates that this map is 'dark', i.e. HM Flash needs to be used in order
    // to see properly.
    is_dark_cave: boolean;

    // Where this map connects to in the overworld (can be up to one per cardinal
    // direction, as well as one for diving/surfacing.
    connections: MapConnection[];

    // Tiles on this map that, when entering, will teleport the player to a
    // different location on another map. This is used for implementing doors.
    warps: MapWarp[];

    // Events triggered by walking onto a tile.
    tile_enter_events: MapTileEnterEvent[];

    // Events triggered by interacting with ('talking to') a tile.
    tile_interact_events: MapTileInteractEvent[];

    // Objects that should be placed on this map.
    // Not all of these objects might be present. Some are toggled on/off depending
    // on some flag's value, and some objects might be NPCs that walk around and so
    // are in different positions than `local_coordinates` indicates. (The range of
    // their movement is defined by `movement.range`.)
    object_templates: MapObjectTemplate[];
};

type MapTileData = {
    local_coordinates: [number, number];

    // Usually 3 for land tiles and 0 for water tiles, does not _really_ indicate
    // whether this is a hill or not.
    elevation: number;

    type: string;

    // Whether wild Pokémon might be encountered here.
    has_encounters: boolean;

    // Whether the player can collide with this tile, i.e. it is inaccessible.
    // Since this data structure is currently only used for tiles the player is
    // standing on, this should always be `false`.
    collision: boolean;

    // Whether this is a surfable water tile.
    is_surfing_possible: boolean;
};

export type MapLocation = {
    // General information about the map.
    map: MapData;

    // x and y coordinates of the current player location.
    player_position: [number, number];

    // Information about _all_ the tiles on that map, indexed by x/y.
    tiles: MapTileData[][];
};

export type Player = {
    name: string;
    gender: "male" | "female";

    trainer_id: number;
    secret_id: number;

    money: number;
    coins: number;

    registered_item: string;
};

export type PlayerAvatar = {
    map_group_and_number: [number, number];

    // Local coordinates (in tiles) on the current map.
    local_coordinates: [number, number];

    running_state: "NOT_MOVING" | "TURN_DIRECTION" | "MOVING";
    tile_transition_state: "NOT_MOVING" | "TRANSITIONING" | "CENTERING";
    acro_bike_state: "NORMAL" | "TURNING" | "STANDING_WHEELIE" | "HOPPING_WHEELIE" | "MOVING_WHEELIE";
    on_bike: boolean;
    facing_direction: "Down" | "Up" | "Left" | "Right";

    flags: {
        OnFoot: boolean;
        OnMachBike: boolean;
        OnAcroBike: boolean;
        Surfing: boolean;
        Underwater: boolean;
        Controllable: boolean;
        ForciblyMoving: boolean;
        Dash: boolean;
    };
};

type PokemonStorageSlot = {
    slot_index: number;
    row: number;
    column: number;
    pokemon: Pokemon;
};

type PokemonStorageBox = {
    name: string;
    wallpaper_id: number;

    // A list of all _used_ slots in this box.
    slots: PokemonStorageSlot[];
};

export type PokemonStorage = {
    active_box_index: number;
    pokemon_count: number;
    boxes: PokemonStorageBox[];
};

type ItemSlot = {
    item: Item;
    quantity: number;
}

// Items that the player is carrying.
export type ItemBag = {
    items: ItemSlot[];
    key_items: ItemSlot[];
    poke_balls: ItemSlot[];
    tms_hms: ItemSlot[];
    berries: ItemSlot[];
}

// Items that are stored in the PC.
export type ItemStorage = ItemSlot[];
