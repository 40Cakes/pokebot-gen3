// 40 Cakes' Stream Overlay
// Ported over from the Bizhawk bot, consider this overlay an *alpha* with the libmgba bot
// If you do decide to stream this yourself, please at least try to put your own unique spin on the design/or layout!
// This is intended to be loaded into OBS as a browser source, with a resolution of 2560x1440

// Start date for the top-left "time elapsed since challenge started" timer
start_date = "2023-01-01"
time_zone = "Australia/Sydney" // "Australia/Sydney"
override_display_timezone = "AEST" // "AEST"

// Name of Pokemon for the "timers since last encounter" for a Pokemon to display on screen
target_timer_1 = "Aron" // "Seedot"
target_timer_2 = ""

// Pokemon to display on the checklist (possible encounters via current bot mode are appended to top of list)
// Leave it empty to only show encounters on the current route
// TODO: Currently limited to the # of mon that can be displayed before table overflows - look at adding auto scrolling
pokemon_checklist = {
    "Gulpin": {
        "goal": 2,
        "hidden": false
    },
    "Plusle": {
        "goal": 1,
        "hidden": false
    },
    "Minun": {
        "goal": 1,
        "hidden": false
    },
    "Oddish": {
        "goal": 2,
        "hidden": false
    },
    "Electrike": {
        "goal": 2,
        "hidden": false
    },
    "Illumise": {
        "goal": 1,
        "hidden": false
    },
    "Volbeat": {
        "goal": 1,
        "hidden": false
    },
    "Makuhita": {
        "goal": 2,
        "hidden": false
    },
    "Geodude": {
        "goal": 2,
        "hidden": false
    },
    "Zubat": {
        "goal": 3,
        "hidden": false
    },
    "Aron": {
        "goal": 3,
        "hidden": false
    },
    "Sableye": {
        "goal": 1,
        "hidden": false
    },
    "Magikarp": {
        "goal": 2,
        "hidden": true
    },
    "Tentacool": {
        "goal": 2,
        "hidden": true
    },
    "Goldeen": {
        "goal": 2,
        "hidden": true
    },
}

/**
 * Stores latest result of each API call so that the data is easily available for all functions.
 * @type {{
 *     emulator: PokeBotApi.GetEmulatorResponse,
 *     game_state: PokeBotApi.GetGameStateResponse,
 *     stats: PokeBotApi.GetStatsResponse,
 *     shiny_log: PokeBotApi.GetShinyLogResponse,
 *     event_flags: PokeBotApi.GetEventFlagsResponse,
 *     opponent: StreamEvents.WildEncounter,
 *     checklist: null,
 *     bot_mode: string | null,
 *     map: PokeBotApi.GetMapResponse,
 *     map_encounters: PokeBotApi.GetMapEncountersResponse,
 *     party: PokeBotApi.GetPartyResponse,
 *     player: PokeBotApi.GetPlayerResponse,
 * }}
 */
const state = {
    stats: null,
    event_flags: null,
    emulator: null,
    bot_mode: null,
    game_state: null,
    party: null,
    opponent: null,
    map: null,
    map_encounters: null,
    player: null,
    shiny_log: null,
    checklist: null
}

const dateFormatter = Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    hour12: true,
    timeZone: time_zone,
});
let $localTime;

timers()

// Init encounter log table with empty entries
let $encounterLog = $("#encounter_log");

$encounterLog.empty()
for (var i = 0; i < 8; i++) {
    $encounterLog.append(
        $("<tr>")
            .append($("<td>")
                .append($("<div>")
                    .append($("<img>")
                        .addClass("sprite")
                        .attr({ "src": "sprites/items/None.png" }))))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
            .append($("<td>").text(""))
    )
}

const initialData = [
    fetch("/event_flags")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetEventFlagsResponse} */
            handleEventFlags(data)
        }),

    fetch("/emulator")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetEmulatorResponse} */
            handlePerformanceData({ encounter_rate: 0 })
            handleBotMode(data.bot_mode)
            initBadges({ game: data.game.title })
        }),

    fetch("/game_state")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetGameStateResponse} */
            handleGameState(data)
        }),

    fetch("/party")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetPartyResponse} */
            handleParty(data)
        }),

    fetch("/map_encounters")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetMapEncountersResponse} */
            handleMapEncounters(data)
        }),

    fetch("/map")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetMapResponse} */
            handleMap(data)
        }),

    /** @var {PokeBotApi.GetPlayerResponse} */
    fetch("/player")
        .then(response => response.json())
        .then(data => {
            handlePlayer(data)
        }),

    fetch("/stats")
        .then(response => response.json())
        .then(data => {
            handleStats(data)
        }),

    fetch("/encounter_log")
        .then(response => response.json())
        .then(data => {
            for (let index = 0; index < 9; index++) {
                if (data.length >= index + 1) {
                    if (index === 0) {
                        handleWildEncounter(data[index]);
                    } else {
                        appendEncounterLog(data[index].pokemon);
                    }
                }
            }
        }),
]

const url = new URL(window.location.origin + "/stream_events")
url.searchParams.append("topic", "PerformanceData")
url.searchParams.append("topic", "BotMode")
url.searchParams.append("topic", "GameState")
url.searchParams.append("topic", "Party")
url.searchParams.append("topic", "WildEncounter")
url.searchParams.append("topic", "Map")
url.searchParams.append("topic", "MapEncounters")
url.searchParams.append("topic", "Player")
url.searchParams.append("topic", "Inputs")

Promise.all(initialData).then(() => {
    const eventSource = new EventSource(url)
    eventSource.addEventListener("PerformanceData", event => handlePerformanceData(JSON.parse(event.data)))
    eventSource.addEventListener("BotMode", event => handleBotMode(JSON.parse(event.data)))
    eventSource.addEventListener("GameState", event => handleGameState(JSON.parse(event.data)))
    eventSource.addEventListener("Party", event => handleParty(JSON.parse(event.data)))
    eventSource.addEventListener("WildEncounter", event => handleWildEncounter(JSON.parse(event.data)))
    eventSource.addEventListener("MapChange", event => handleMap(JSON.parse(event.data)))
    eventSource.addEventListener("MapEncounters", event => handleMapEncounters(JSON.parse(event.data)))
    eventSource.addEventListener("Player", event => handlePlayer(JSON.parse(event.data)))
    eventSource.addEventListener("Inputs", event => handleInput(JSON.parse(event.data)))

    refreshchecklist()
    refreshShinyLog()
})

async function handleStats(data) {
    if (data === null) {
        return
    }

    state.stats = data

    if (target_timer_1 !== "" && data.pokemon[target_timer_1]) {
        $("#target_1_sprite").attr("src", pokemonSprite(target_timer_1, false, false, true))
        $("#target_1").css("display", "inline-block")
    }

    if (target_timer_2 !== "" && data.pokemon[target_timer_2]) {
        $("#target_2_sprite").attr("src", pokemonSprite(target_timer_2, false, false, true))
        $("#target_2").css("display", "inline-block")
    }
}

/** @param {PokeBotApi.GetEventFlagsResponse} data */
function handleEventFlags(data) {
    if (data === null) {
        return
    }

    state.event_flags = data

    for (var i = 0; i < 8; i++) {
        if (data["BADGE0" + (i + 1).toString() + "_GET"]) {
            document.getElementById("badge" + i.toString()).className = "badge_earned"
        }
    }
}

/** @param {StreamEvents.BotMode} data */
function handleBotMode(data) {
    if (data === null) {
        return
    }

    state.bot_mode = data
}

/** @param {StreamEvents.PerformanceData} data */
function handlePerformanceData(data) {
    if (data === null) {
        return
    }

    state.emulator = data

    if (data.encounter_rate > 0) {
        document.getElementById("encounter_rate").innerText = data.encounter_rate.toLocaleString("en-GB")
    }
}

/** @param {StreamEvents.Party} data */
function handleParty(data) {
    if (data === null) {
        return
    }

    state.party = data

    for (var i = 0; i < 6; i++) {
        if (typeof data[i] !== "undefined") {
            $("#party" + i.toString()).attr("src", pokemonSprite(data[i].species.name, data[i].is_shiny, false, true))
        }
    }
}

/** @param {StreamEvents.WildEncounter} data */
async function handleWildEncounter(data) {
    if (data === null) {
        return
    }

    if (state.opponent !== null && state.opponent.encounter_id === data.encounter_id) {
        return
    }

    state.opponent = data

    await fetch("/stats")
        .then(response => response.json())
        .then(total_stats => {
            if (total_stats === null) {
                return
            }
            state.stats = total_stats
        })

    refreshchecklist()
    refreshShinyLog()
    appendEncounterLog(data.pokemon)

    document.getElementById("total_shiny").innerText = (state.stats.totals.shiny_encounters) ? state.stats.totals.shiny_encounters.toLocaleString() : 0
    document.getElementById("total_encounters").innerText = (state.stats.totals.total_encounters) ? state.stats.totals.total_encounters.toLocaleString() : 0

    // Update total shiny average
    document.getElementById("shiny_average").innerText = shinyAverage(state.stats.totals);

    // Update encounter HUD
    const pokemon = data.pokemon;
    document.getElementById("encounter_hud_pid").innerText = pokemon.personality_value.toString(16)
    document.getElementById("encounter_hud_hp").innerText = pokemon.ivs.hp
    document.getElementById("encounter_hud_hp").className = IVColour(pokemon.ivs.hp)
    document.getElementById("encounter_hud_attack").innerText = pokemon.ivs.attack
    document.getElementById("encounter_hud_attack").className = IVColour(pokemon.ivs.attack)
    document.getElementById("encounter_hud_defence").innerText = pokemon.ivs.defence
    document.getElementById("encounter_hud_defence").className = IVColour(pokemon.ivs.defence)
    document.getElementById("encounter_hud_special_attack").innerText = pokemon.ivs.special_attack
    document.getElementById("encounter_hud_special_attack").className = IVColour(pokemon.ivs.special_attack)
    document.getElementById("encounter_hud_special_defence").innerText = pokemon.ivs.special_defence
    document.getElementById("encounter_hud_special_defence").className = IVColour(pokemon.ivs.special_defence)
    document.getElementById("encounter_hud_speed").innerText = pokemon.ivs.speed
    document.getElementById("encounter_hud_speed").className = IVColour(pokemon.ivs.speed)

    document.getElementById("encounter_hud_nature").innerText = pokemon.nature.name
    $("#encounter_hud_hidden_power").attr("src", "sprites/types/large/" + pokemon.hidden_power_type.name + ".png")

    if (pokemon.held_item != null) {
        $("#encounter_hud_item").attr("src", "sprites/items/" + pokemon.held_item.name + ".png")
    } else {
        $("#encounter_hud_item").attr("src", "sprites/items/None.png")
    }

    document.getElementById("encounter_sv").innerText = pokemon.shiny_value.toLocaleString()
    document.getElementById("encounter_sv").className = SVColour(pokemon.shiny_value)
    $("#encounter_sv_label").attr("src", SVImage(pokemon.shiny_value))

    $("#encounter_hud").css("opacity", "100%")
    $("#sv_hud").css("opacity", "100%")

    if (!pokemon.is_shiny) {
        // Update phase stats
        // Don't update phase stats on shinies (OBS screenshot)

        // PSP
        document.getElementById("psp").innerText = calcPSP(state.stats.current_phase.encounters)
        // Phase encounters
        document.getElementById("phase_encounters").innerText = state.stats.current_phase.encounters.toLocaleString()

        // Phase streak
        $("#phase_streak_sprite").attr("src", pokemonSprite(state.stats.current_phase.longest_streak.species_name, false, false, false))
        document.getElementById("phase_streak").innerText = state.stats.current_phase.longest_streak.value.toLocaleString()
        document.getElementById("current_streak").innerText = "(" + state.stats.current_phase.current_streak.value.toLocaleString() + ")"

        // Phase IV records
        $("#phase_iv_record_high_sprite").attr("src", pokemonSprite(state.stats.current_phase.highest_iv_sum.species_name, false, false, false))
        document.getElementById("phase_iv_record_high").innerText = state.stats.current_phase.highest_iv_sum.value
        $("#phase_iv_record_low_sprite").attr("src", pokemonSprite(state.stats.current_phase.lowest_iv_sum.species_name, false, false, false))
        document.getElementById("phase_iv_record_low").innerText = state.stats.current_phase.lowest_iv_sum.value

        // Total IV records
        $("#total_iv_record_high_sprite").attr("src", pokemonSprite(state.stats.totals.total_highest_iv_sum.species_name, false, false, false))
        document.getElementById("total_iv_record_high").innerText = state.stats.totals.total_highest_iv_sum.value
        $("#total_iv_record_low_sprite").attr("src", pokemonSprite(state.stats.totals.total_lowest_iv_sum.species_name, false, false, false))
        document.getElementById("total_iv_record_low").innerText = state.stats.totals.total_lowest_iv_sum.value

        // Phase encounter records
        if (state.stats.longest_phase.species_name !== null && state.stats.shortest_phase.species_name !== null) {
            $("#longest_phase_sprite").attr("src", pokemonSprite(state.stats.longest_phase.species_name, true))
            document.getElementById("longest_phase_encounters").innerText = state.stats.longest_phase.value.toLocaleString()
            $("#shortest_phase_sprite").attr("src", pokemonSprite(state.stats.shortest_phase.species_name, true))
            document.getElementById("shortest_phase_encounters").innerText = state.stats.shortest_phase.value.toLocaleString()
        }
    }
}

/** @param {StreamEvents.MapChange} data */
function handleMap(data) {
    if (data === null) {
        return
    }

    state.map = data

    document.getElementById("location").innerText = data.map.name
}

/** @param {StreamEvents.MapEncounters} data */
function handleMapEncounters(data) {
    state.map_encounters = data;

    if (data.effective.repel_level > 0) {
        $("#repel_level").text(data.effective.repel_level);
        $("#repel_info").css("display", "inline-block");
    } else {
        $("#repel_info").css("display", "none");
    }
}

/** @param {StreamEvents.Player} data */
function handlePlayer(data) {
    if (data === null) {
        return
    }

    state.player = data
}

/** @param {StreamEvents.GameState} data */
function handleGameState(data) {
    if (data === null) {
        return
    }

    state.game_state = data

    // Hide encounter HUD if outside of battle
    if (!["BATTLE", "BATTLE_ENDING"].includes(data)) {
        $("#encounter_hud").css("opacity", "0%")
        $("#sv_hud").css("opacity", "0%")
    }
}

/** @param {StreamEvents.Inputs} data */
function handleInput(data) {
    if (data === null) {
        return
    }

    if (data.length === 0) {
        // Reset buttons
        $("#input_d_pad").attr("src", "sprites/stream-overlay/inputs/D_Pad.png")
        document.getElementById("input_d_pad").classList.remove("input_pressed")
        document.getElementById("input_start_button").classList.remove("input_pressed")
        document.getElementById("input_select_button").classList.remove("input_pressed")
        document.getElementById("input_b_button").classList.remove("input_pressed")
        document.getElementById("input_a_button").classList.remove("input_pressed")
    } else {
        if (data.includes("Left")) {
            $("#input_d_pad").attr("src", "sprites/stream-overlay/inputs/D_Pad_Left.png")
            document.getElementById("input_d_pad").classList.add("input_pressed")
        } else if (data.includes("Right")) {
            $("#input_d_pad").attr("src", "sprites/stream-overlay/inputs/D_Pad_Right.png")
            document.getElementById("input_d_pad").classList.add("input_pressed")
        } else if (data.includes("Up")) {
            $("#input_d_pad").attr("src", "sprites/stream-overlay/inputs/D_Pad_Up.png")
            document.getElementById("input_d_pad").classList.add("input_pressed")
        } else if (data.includes("Down")) {
            $("#input_d_pad").attr("src", "sprites/stream-overlay/inputs/D_Pad_Down.png")
            document.getElementById("input_d_pad").classList.add("input_pressed")
        }

        if (data.includes("Start")) {
            document.getElementById("input_start_button").classList.add("input_pressed")
        }
        if (data.includes("Select")) {
            document.getElementById("input_select_button").classList.add("input_pressed")
        }
        if (data.includes("B")) {
            document.getElementById("input_b_button").classList.add("input_pressed")
        }
        if (data.includes("A")) {
            document.getElementById("input_a_button").classList.add("input_pressed")
        }
    }
}

function appendEncounterLog(data) {
    if (data.held_item === null) {
        data.held_item = { "name": "None" }
    }

    iv_sum = data.ivs.hp
        + data.ivs.attack
        + data.ivs.defence
        + data.ivs.special_attack
        + data.ivs.special_defence
        + data.ivs.speed

    $encounterLog.prepend(
        $("<tr>")
            .append($("<td>")
                .append($("<div>")
                    .append($("<img>")
                        .addClass("sprite")
                        .attr({ "src": pokemonSprite(data.species.name, data.is_shiny, data.is_anti_shiny, false) }))
                    .append($("<img>").attr({ "src": "sprites/items/" + data.held_item.name + ".png" })
                        .addClass("encounter_log_held_item"))))
            .append($("<td>")
                .addClass(IVColour(data.ivs.hp))
                .text(data.ivs.hp))
            .append($("<td>")
                .addClass(IVColour(data.ivs.attack))
                .text(data.ivs.attack))
            .append($("<td>")
                .addClass(IVColour(data.ivs.defence))
                .text(data.ivs.defence))
            .append($("<td>")
                .addClass(IVColour(data.ivs.special_attack))
                .text(data.ivs.special_attack))
            .append($("<td>")
                .addClass(IVColour(data.ivs.special_defence))
                .text(data.ivs.special_defence))
            .append($("<td>")
                .addClass(IVColour(data.ivs.speed))
                .text(data.ivs.speed))
            .append($("<td>")
                .addClass(IVSumColour(iv_sum))
                .text(iv_sum))
            .append($("<td>")
                .addClass(SVColour(data.shiny_value))
                .text(data.shiny_value.toLocaleString()))
    )

    $encounterLog.children().slice(8).detach()
}

function refreshShinyLog() {
    $("#shiny_log").empty()

    for (var i = 0; i < 8; i++) {
        if (state.shiny_log === null || state.shiny_log.length <= i || typeof state.shiny_log[i] === "undefined") {
            $("#shiny_log").append($("<tr>")
                .append($("<td>").text(""))
                .append($("<td>")
                    .append($("<img>")
                        .addClass("sprite")
                        .attr({ "src": "sprites/items/None.png" })))
                .append($("<td>").text(""))
                .append($("<td>").text(""))
                .append($("<td>").text(""))
                .append($("<td>").text(""))
                .append($("<td>").text(""))
                .append($("<td>").text(""))
                .append($("<td>").text(""))
            )
        } else {
            let start = new Date(state.shiny_log[i].phase.start_time);
            let end = new Date(state.shiny_log[i].phase.end_time);
            let deltaInSeconds = (end.getTime() - start.getTime()) / 1000;

            let duration = "";
            let durationUnit = "";

            if (deltaInSeconds < 3570) {
                duration = Math.round(deltaInSeconds / 60);
                durationUnit = "min";
            } else if (deltaInSeconds < 36000) {
                duration = (deltaInSeconds / 3600).toLocaleString("en", {maximumFractionDigits: 1});
                durationUnit = "hr";
            } else if (deltaInSeconds < 360000) {
                duration = Math.round(deltaInSeconds / 3600);
                durationUnit = "hr";
            } else if (deltaInSeconds < 864000) {
                duration = (deltaInSeconds / 86400).toLocaleString("en", {maximumFractionDigits: 1});
                durationUnit = "d";
            } else {
                duration = Math.round(deltaInSeconds / 86400);
                durationUnit = "d";
            }

            let secondsAgo = (new Date().getTime() - end.getTime()) / 1000;
            let timeAgo = "";
            let timeAgoUnit = "";

            if (secondsAgo < 59.5 * 60) {
                timeAgo = Math.round(secondsAgo / 60);
                timeAgoUnit = "M";
            } else if (secondsAgo < 23.5 * 3600) {
                timeAgo = Math.round(secondsAgo / 3600);
                timeAgoUnit = "HR";
            } else {
                timeAgo = Math.round(secondsAgo / 86400);
                timeAgoUnit = "D";
            }

            const spriteColumn = $("<td>")
                .append($("<img>")
                    .addClass("sprite")
                    .attr({ "src": pokemonSprite(state.shiny_log[i].shiny_encounter.pokemon.species.name, true, false, false) }));
            if (![null, "Caught"].includes(state.shiny_log[i].shiny_encounter.outcome)) {
                spriteColumn
                    .addClass("missed")
                    .append($("<img>").attr("src", "sprites/stream-overlay/cross.png").addClass("crossed-out"));
            }

            $("#shiny_log").append($("<tr>")
                .append($("<td>")
                    .css({ "font-size": "1.333rem" })
                    .text(`${timeAgo} ${timeAgoUnit}`))
                .append(spriteColumn)
                .append($("<td>")
                    .addClass("sv_yellow")
                    .text(state.shiny_log[i].shiny_encounter.pokemon.shiny_value))
                .append($("<td>")
                    .text(state.shiny_log[i].phase.encounters.toLocaleString()))
                .append($("<td>")
                    .css({ "font-size": "1.333rem" })
                    .text(duration)
                    .append($("<span>")
                        .css({ "font-size": "1rem" })
                        .text(" " + durationUnit)))
                .append($("<td>")
                    .css({ "font-size": "1.333rem" })
                    .text(calcPSP(state.shiny_log[i].phase.encounters).toPrecision(3).toString() + "%"))
                .append($("<td>")
                    .text(intShortName(state.shiny_log[i].snapshot.species_encounters ?? 0, 3)))
                .append($("<td>")
                    .text((state.shiny_log[i].snapshot.species_shiny_encounters ?? 0).toLocaleString()))
                .append($("<td>")
                    .text(intShortName(state.shiny_log[i].snapshot.total_encounters, 3)))
            )
        }
    }
}

function initBadges(title) {
    if (["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"].includes(title.game)) {
        var badges = ["Stone", "Knuckle", "Dynamo", "Heat", "Balance", "Feather", "Mind", "Rain"]
    }
    else if (["POKEMON FIRE", "POKEMON LEAF"].includes(title.game)) {
        var badges = ["Boulder", "Cascade", "Thunder", "Rainbow", "Soul", "Marsh", "Volcano", "Earth"]
    }

    for (var i = 0; i < 8; i++) {
        $("#badge" + i.toString()).attr("src", "sprites/badges/" + badges[i] + ".png")
    }
}

async function refreshchecklist() {
    $("#checklist").empty()

    if (state.stats === null) {
        return
    }

    // Refresh stats on first encounter of phase
    if (state.stats.current_phase.encounters == 1) {
        await fetch("/stats")
            .then(response => response.json())
            .then(stats => {
                if (stats === null) {
                    return
                }
                state.stats = stats
            })
    }

    // Get encounter rates for the current map + bot mode
    let last_encounter_type = state.opponent?.type ?? "land";

    /** @type {MapEncounter[]} */
    let encounters = [];
    if (state.map_encounters !== null) {
        if (last_encounter_type === "land") {
            encounters = state.map_encounters.effective.land_encounters;
        } else if (last_encounter_type === "surfing") {
            encounters = state.map_encounters.effective.surf_encounters;
        } else if (last_encounter_type === "rock_smash") {
            encounters = state.map_encounters.effective.rock_smash_encounters;
        } else if (last_encounter_type === "fishing_old_rod") {
            encounters = state.map_encounters.effective.old_rod_encounters;
        } else if (last_encounter_type === "fishing_good_rod") {
            encounters = state.map_encounters.effective.good_rod_encounters;
        } else if (last_encounter_type === "fishing_super_rod") {
            encounters = state.map_encounters.effective.super_rod_encounters;
        }
    }

    mode_encounters = {}
    route_checklist = {}
    encounters.forEach(encounter => {
        if (mode_encounters[encounter.species_name]) {
            mode_encounters[encounter.species_name] += Math.round(100 * encounter.encounter_rate)
        } else {
            mode_encounters[encounter.species_name] = Math.round(100 * encounter.encounter_rate)
        }

        if (!pokemon_checklist[encounter.species_name]) {
            route_checklist[encounter.species_name] = {
                "goal": 0,
                "hidden": false
            }
        }
    })

    checklist_progress = 0
    checklist_required_mons = 0

    for (const [name, obj] of Object.entries(Object.assign({}, route_checklist, pokemon_checklist))) {
        checklist_mon = {}
        checklist_mon.location_rate = (mode_encounters[name] != null) ? mode_encounters[name] + "%" : ""

        if (!state.stats.pokemon[name]) {
            // 99999 is just used as a "null" value so .toLocaleString() doesn't complain
            checklist_mon.shiny_encounters = 0
            checklist_mon.catches = 0
            checklist_mon.phase_encounters = 0
            checklist_mon.encounters = 0
            checklist_mon.phase_lowest_sv = 99999
            checklist_mon.phase_highest_sv = 99999
            checklist_mon.phase_highest_iv_sum = 99999
            checklist_mon.phase_lowest_iv_sum = 99999
            checklist_mon.phase_percent = ""
            checklist_mon.shiny_average = ""
        } else {
            checklist_mon.shiny_encounters = (state.stats.pokemon[name].shiny_encounters != null) ? state.stats.pokemon[name].shiny_encounters : 0
            checklist_mon.catches = (state.stats.pokemon[name].catches != null) ? state.stats.pokemon[name].catches : 0
            checklist_mon.phase_encounters = (state.stats.pokemon[name].phase_encounters != null) ? state.stats.pokemon[name].phase_encounters : 0
            checklist_mon.encounters = (state.stats.pokemon[name].total_encounters != null) ? state.stats.pokemon[name].total_encounters : 0
            checklist_mon.phase_lowest_sv = (state.stats.pokemon[name].phase_lowest_sv != null) ? state.stats.pokemon[name].phase_lowest_sv : 99999
            checklist_mon.phase_highest_sv = (state.stats.pokemon[name].phase_highest_sv != null) ? state.stats.pokemon[name].phase_highest_sv : 99999
            checklist_mon.phase_highest_iv_sum = (state.stats.pokemon[name].phase_highest_iv_sum != null) ? state.stats.pokemon[name].phase_highest_iv_sum : 99999
            checklist_mon.phase_lowest_iv_sum = (state.stats.pokemon[name].phase_lowest_iv_sum != null) ? state.stats.pokemon[name].phase_lowest_iv_sum : 99999
            checklist_mon.phase_percent = (state.stats.pokemon[name].phase_encounters > 0) ? ((state.stats.pokemon[name].phase_encounters / state.stats.totals.total_encounters) * 100).toPrecision(4) + "%" : ""

            checklist_mon.shiny_average = shinyAverage(state.stats.pokemon[name]);
            if (checklist_mon.shiny_average === "N/A") {
                checklist_mon.shiny_average = "";
            } else {
                checklist_mon.shiny_average = `(${checklist_mon.shiny_average})`;
            }
        }

        checklist_required_mons += obj.goal
        checklist_progress += Math.min(obj.goal, checklist_mon.catches)

        if (!obj.hidden) {
            animated_sprite = false
            if (state.opponent?.pokemon?.species?.name === name) {
                animated_sprite = true
            }

            $("#checklist").append($("<tr>")
                .addClass("checklist")
                .append($("<td>")
                    .append($("<img>")
                        .addClass("checklist-sprite")
                        .attr({ "src": pokemonSprite(name, true, false, animated_sprite) })))
                .append($("<td>")
                    .text(checklist_mon.location_rate))
                .append($("<td>")
                    .append($("<span>")
                        .addClass(SVColour(checklist_mon.phase_lowest_sv))
                        .text(checklist_mon.phase_lowest_sv.toLocaleString()))
                    .append($("<br>"))
                    .append($("<span>")
                        .addClass(SVColour(checklist_mon.phase_highest_sv))
                        .text(checklist_mon.phase_highest_sv.toLocaleString())))
                .append($("<td>")
                    .append($("<span>")
                        .addClass(IVSumColour(checklist_mon.phase_highest_iv_sum))
                        .text(checklist_mon.phase_highest_iv_sum.toLocaleString()))
                    .append($("<br>"))
                    .append($("<span>")
                        .addClass(IVSumColour(checklist_mon.phase_lowest_iv_sum))
                        .text(checklist_mon.phase_lowest_iv_sum.toLocaleString())))
                .append($("<td>")
                    .text(checklist_mon.phase_encounters.toLocaleString())
                    .append($("<br>"))
                    .append($("<span>")
                        .addClass("checklist_phase_percent")
                        .text(checklist_mon.phase_percent)))
                .append($("<td>")
                    .text(intShortName(checklist_mon.encounters, 3)))
                .append($("<td>")
                    .text(checklist_mon.catches.toLocaleString())
                    .append($("<span>")
                        .addClass("checklist_goal")
                        .text((obj.goal) ? "/" + obj.goal : ""))
                    .append($("<br>"))
                    .append($("<span>")
                        .addClass("checklist_phase_percent")
                        .text(checklist_mon.shiny_average)))
                .append($("<td>")
                    .append($("<img>")
                        .addClass("checklist-tick")
                        .attr({ "src": (!obj.goal || checklist_mon.catches >= obj.goal) ? "sprites/stream-overlay/tick.png" : "sprites/items/None.png" })))
            )
        }
    }

    checklist_percent = (checklist_progress / checklist_required_mons) * 100
    $("#progress_bar_fill").css("width", checklist_percent + "%")
    if (checklist_percent === 100) {
        $("#progress_bar_fill").css("background-color", "#16c40c")
    }

    var rows = $("#checklist tr").get();

    rows.sort(function (a, b) {
        var A = $(a).find("td:eq(1)").text().trim();
        var B = $(b).find("td:eq(1)").text().trim();

        A = A === "" ? 0 : parseFloat(A.replace("%", ""));
        B = B === "" ? 0 : parseFloat(B.replace("%", ""));

        return A - B;
    });

    $.each(rows, function (index, row) {
        $("#checklist").prepend(row);
    })
}

function timers() {
    $("#start_days").text(diffDays(start_date))
    $("#start_hours").text(diffHrs(start_date))

    if (!$localTime) {
        $localTime = $("#local_time");
        $("#time_zone").text(
            override_display_timezone
                ? override_display_timezone
                : new Date().toLocaleDateString("en-US", {timeZoneName: "short", timeZone: time_zone})
                    .split(" ")[1]
        );
    }

    $localTime.text(dateFormatter.format(new Date()));

    if (state.opponent !== null) {
        if ((state.shiny_log == null) || (state.opponent.pokemon.is_shiny && state.opponent.encounter_id !== state.shiny_log[0].shiny_encounter.encounter_id)) {
            // TEMP/hacky way to ensure shiny log is updated when current opponent is shiny
            fetch("/shiny_log?limit=9")
                .then(response => response.json())
                .then(data => {
                    if (data !== null) {
                        state.shiny_log = data
                    }

                    refreshShinyLog()
                })

            fetch("/stats")
                .then(response => response.json())
                .then(data => {
                    handleStats(data)
                })
        } else if (state.shiny_log[0] !== undefined && !state.opponent.pokemon.is_shiny) {
            // Don't update phase time on shinies (for OBS screenshot)
            $("#phase_time_hrs").text((diffDays(new Date(state.shiny_log[0].phase.end_time)) * 24) + (diffHrs(new Date(state.shiny_log[0].phase.end_time))))
            $("#phase_time_mins").text(diffMins(new Date(state.shiny_log[0].phase.end_time)))
        }
    }

    if (state.stats !== null) {
        if (target_timer_1 !== "" && state.stats.pokemon[target_timer_1] !== undefined) {
            let target_date = new Date(state.stats.pokemon[target_timer_1].last_encounter_time)
            target_timer_hrs = diffHrs(target_date).toLocaleString()
            target_timer_mins = diffMins(target_date).toLocaleString()
            $("#target_1_timer_hrs").text(target_timer_hrs)
            $("#target_1_timer_mins").text(target_timer_mins)
        }

        if (target_timer_2 !== "" && state.stats.pokemon[target_timer_2] !== undefined) {
            let target_date = new Date(state.stats.pokemon[target_timer_2].last_encounter_time)
            target_timer_hrs = diffHrs(target_date).toLocaleString()
            target_timer_mins = diffMins(target_date).toLocaleString()
            $("#target_2_timer_hrs").text(target_timer_hrs)
            $("#target_2_timer_mins").text(target_timer_mins)
        }
    }

    t = setTimeout(function () {
        timers()
    }, 500)
}

function pokemonSprite(name, shiny, anti, animated) {
    if (animated) {
        if (shiny) {
            return "sprites/pokemon-animated/shiny/" + name + ".gif"
        }

        return "sprites/pokemon-animated/normal/" + name + ".gif"
    }

    if (shiny) {
        return "sprites/pokemon/shiny/" + name + ".png"
    }
    if (anti) {
        return "sprites/pokemon/anti-shiny/" + name + ".png"
    }

    return "sprites/pokemon/normal/" + name + ".png"
}

function SVImage(sv) {
    switch (true) {
        case (sv < 8):
            return "sprites/stream-overlay/sparkles.png"
        case (sv > 65527):
            return "sprites/stream-overlay/anti-sparkles.png"
        default:
            return "sprites/stream-overlay/cross.png"
    }
}

function SVColour(sv) {
    switch (true) {
        case (sv === 99999):
            return "sv_null"
        case (sv < 8):
            return "sv_yellow"
        case (sv > 65527):
            return "sv_purple"
        default:
            return "sv_red"
    }
}

function IVColour(iv) {
    switch (true) {
        case (iv === 99999):
            return "iv_null"
        case (iv === 31):
            return "iv_yellow"
        case (iv === 0):
            return "iv_purple"
        case (iv >= 26):
            return "iv_green"
        case (iv <= 5):
            return "iv_red"
        default:
            return "iv_white"
    }
}

function IVSumColour(iv_sum) {
    switch (true) {
        case (iv_sum === 99999):
            return "iv_null"
        case (iv_sum === 186):
            return "iv_yellow"
        case (iv_sum === 0):
            return "iv_purple"
        case (iv_sum >= 140):
            return "iv_green"
        case (iv_sum <= 50):
            return "iv_red"
        default:
            return "iv_white"
    }
}

function calcPSP(encounters) {
    var binomialDistribution = function (b, a) {
        c = Math.pow(1 - a, b)
        return 100 * (c * Math.pow(-(1 / (a - 1)), b) - c)
    }

    var chance = binomialDistribution(encounters, 1 / 8192)
    var cumulative_odds = Math.floor(chance * 100) / 100
    if (cumulative_odds === 100 || isNaN(cumulative_odds)) cumulative_odds = "99.99"

    return cumulative_odds
}

function clamp(number, min, max) {
    return Math.max(min, Math.min(number, max))
}

/**
 * @param {EncounterSummary|EncounterTotals} summary
 * @return {string}
 */
function shinyAverage(summary) {
    if (summary.shiny_encounters === null || summary.total_encounters === null || summary.shiny_encounters === 0) {
        return "N/A";
    } else {
        return "1/" + Math.round(summary.total_encounters / summary.shiny_encounters).toLocaleString("en");
    }
}

function diffMs(time) {
    var now = new Date()
    var start = time instanceof Date ? time : new Date(time)
    return (now - start)
}

function diffMins(time) {
    return clamp(Math.round(((diffMs(time) % 86400000) % 3600000) / 60000), 0, 59)
}

function diffHrs(time) {
    return Math.floor((diffMs(time) % 86400000) / 3600000)
}

function diffDays(time) {
    return Math.floor(diffMs(time) / 86400000)
}

function intShortName(number, precision) {
    return Math.abs(Number(number)) >= 1.0e+9
        ? (Math.abs(Number(number)) / 1.0e+9).toFixed(precision) + "B"
        : Math.abs(Number(number)) >= 1.0e+6
            ? (Math.abs(Number(number)) / 1.0e+6).toFixed(precision) + "M"
            : Math.abs(Number(number)).toLocaleString();
}
