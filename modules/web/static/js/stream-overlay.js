// 40 Cakes' Stream Overlay
// Ported over from the Bizhawk bot, consider this overlay an *alpha* with the libmgba bot
// If you do decide to stream this yourself, please at least try to put your own unique spin on the design/or layout!
// This is intended to be loaded into OBS as a browser source, with a resolution of 2560x1440

// Start date for the top-left "time elapsed since challenge started" timer
start_date = "2023-01-01"
override_display_timezone = "AEST" // "AEST"

// Name of Pokemon for the "timers since last encounter" for a Pokemon to display on screen
target_timer_1 = "Aron" // "Seedot"
target_timer_2 = "Zubat"

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

// Stores latest result of each API call so that the data is easily available for all functions
state = {
    stats: null,
    event_flags: null,
    emulator: null,
    bot_mode: null,
    game_state: null,
    party: null,
    opponent: null,
    previous_opponent: null,
    map: null,
    player: null,
    shiny_log: null,
    checklist: null
}

timers()
refreshchecklist()
refreshShinyLog()

// Init encounter log table with empty entries
$("#encounter_log").empty()
for (var i = 0; i < 8; i++) {
    $("#encounter_log").append(
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

    fetch("/opponent")
        .then(response => response.json())
        .then(data => {
            /** @var {PokeBotApi.GetOpponentResponse} */
            handleOpponent(data)
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
]

const url = new URL(window.location.origin + "/stream_events")
url.searchParams.append("topic", "PerformanceData")
url.searchParams.append("topic", "BotMode")
url.searchParams.append("topic", "GameState")
url.searchParams.append("topic", "Party")
url.searchParams.append("topic", "Opponent")
url.searchParams.append("topic", "Map")
url.searchParams.append("topic", "Player")
url.searchParams.append("topic", "Inputs")

Promise.all(initialData).then(() => {
    const eventSource = new EventSource(url)
    eventSource.addEventListener("PerformanceData", event => handlePerformanceData(JSON.parse(event.data)))
    eventSource.addEventListener("BotMode", event => handleBotMode(JSON.parse(event.data)))
    eventSource.addEventListener("GameState", event => handleGameState(JSON.parse(event.data)))
    eventSource.addEventListener("Party", event => handleParty(JSON.parse(event.data)))
    eventSource.addEventListener("Opponent", event => handleOpponent(JSON.parse(event.data)))
    eventSource.addEventListener("MapChange", event => handleMap(JSON.parse(event.data)))
    eventSource.addEventListener("Player", event => handlePlayer(JSON.parse(event.data)))
    eventSource.addEventListener("Inputs", event => handleInput(JSON.parse(event.data)))
})

async function handleStats(data) {
    if (data === null) {
        return
    }

    state.stats = data

    if (target_timer_1 !== "" && data.pokemon[target_timer_1]) {
        $("#target_1_sprite").attr("src", pokemonSprite(target_timer_1, false, true))
        $("#target_1").css("opacity", "100%")
    }

    if (target_timer_2 !== "" && data.pokemon[target_timer_2]) {
        $("#target_2_sprite").attr("src", pokemonSprite(target_timer_2, false, true))
        $("#target_2").css("opacity", "100%")
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
            $("#party" + i.toString()).attr("src", pokemonSprite(data[i].species.name, data[i].is_shiny, true))
        }
    }
}

/** @param {StreamEvents.Opponent} data */
async function handleOpponent(data) {
    if (data === null) {
        return
    }
    if (state.opponent !== null && data.personality_value === state.opponent.personality_value) {
        return
    }

    state.opponent = data

    await fetch("/stats?type=pokemon&pokemon=" + data.species.name)
        .then(response => response.json())
        .then(mon_stats => {
            if (mon_stats === null) {
                return
            }
            state.stats.pokemon[data.species.name] = mon_stats
        })

    await fetch("/stats?type=totals")
        .then(response => response.json())
        .then(total_stats => {
            if (total_stats === null) {
                return
            }
            state.stats.totals = total_stats
        })

    refreshchecklist()
    appendEncounterLog(data)

    document.getElementById("total_shiny").innerText = (state.stats.totals.shiny_encounters) ? state.stats.totals.shiny_encounters.toLocaleString() : 0
    document.getElementById("total_encounters").innerText = (state.stats.totals.encounters) ? state.stats.totals.encounters.toLocaleString() : 0

    // Update total shiny average
    if (state.stats.totals.shiny_average) {
        document.getElementById("shiny_average").innerText = state.stats.totals.shiny_average
    } else {
        document.getElementById("shiny_average").innerText = "N/A"
    }

    // Update encounter HUD
    document.getElementById("encounter_hud_pid").innerText = data.personality_value.toString(16)
    document.getElementById("encounter_hud_hp").innerText = data.ivs.hp
    document.getElementById("encounter_hud_hp").className = IVColour(data.ivs.hp)
    document.getElementById("encounter_hud_attack").innerText = data.ivs.attack
    document.getElementById("encounter_hud_attack").className = IVColour(data.ivs.attack)
    document.getElementById("encounter_hud_defence").innerText = data.ivs.defence
    document.getElementById("encounter_hud_defence").className = IVColour(data.ivs.defence)
    document.getElementById("encounter_hud_special_attack").innerText = data.ivs.special_attack
    document.getElementById("encounter_hud_special_attack").className = IVColour(data.ivs.special_attack)
    document.getElementById("encounter_hud_special_defence").innerText = data.ivs.special_defence
    document.getElementById("encounter_hud_special_defence").className = IVColour(data.ivs.special_defence)
    document.getElementById("encounter_hud_speed").innerText = data.ivs.speed
    document.getElementById("encounter_hud_speed").className = IVColour(data.ivs.speed)

    document.getElementById("encounter_hud_nature").innerText = data.nature.name
    $("#encounter_hud_hidden_power").attr("src", "sprites/types/large/" + data.hidden_power_type.name + ".png")

    if (data.held_item != null) {
        $("#encounter_hud_item").attr("src", "sprites/items/" + data.held_item.name + ".png")
    } else {
        $("#encounter_hud_item").attr("src", "sprites/items/None.png")
    }

    document.getElementById("encounter_sv").innerText = data.shiny_value.toLocaleString()
    document.getElementById("encounter_sv").className = SVColour(data.shiny_value)
    $("#encounter_sv_label").attr("src", SVImage(data.shiny_value))

    $("#encounter_hud").css("opacity", "100%")
    $("#sv_hud").css("opacity", "100%")

    if (!data.is_shiny) {
        // Update phase stats
        // Don't update phase stats on shinies (OBS screenshot)

        // PSP
        document.getElementById("psp").innerText = calcPSP(state.stats.totals.phase_encounters)
        // Phase encounters
        document.getElementById("phase_encounters").innerText = state.stats.totals.phase_encounters.toLocaleString()

        // Phase streak
        $("#phase_streak_sprite").attr("src", pokemonSprite(state.stats.totals.phase_streak_pokemon, false, false))
        document.getElementById("phase_streak").innerText = state.stats.totals.phase_streak.toLocaleString()
        document.getElementById("current_streak").innerText = "(" + state.stats.totals.current_streak.toLocaleString() + ")"

        // Phase IV records
        $("#phase_iv_record_high_sprite").attr("src", pokemonSprite(state.stats.totals.phase_highest_iv_sum_pokemon, false, false))
        document.getElementById("phase_iv_record_high").innerText = state.stats.totals.phase_highest_iv_sum
        $("#phase_iv_record_low_sprite").attr("src", pokemonSprite(state.stats.totals.phase_lowest_iv_sum_pokemon, false, false))
        document.getElementById("phase_iv_record_low").innerText = state.stats.totals.phase_lowest_iv_sum

        // Total IV records
        $("#total_iv_record_high_sprite").attr("src", pokemonSprite(state.stats.totals.highest_iv_sum_pokemon, false, false))
        document.getElementById("total_iv_record_high").innerText = state.stats.totals.highest_iv_sum
        $("#total_iv_record_low_sprite").attr("src", pokemonSprite(state.stats.totals.lowest_iv_sum_pokemon, false, false))
        document.getElementById("total_iv_record_low").innerText = state.stats.totals.lowest_iv_sum

        // Phase encounter records
        if (state.stats.totals.longest_phase_encounters !== undefined && state.stats.totals.shortest_phase_encounters !== undefined) {
            $("#longest_phase_sprite").attr("src", pokemonSprite(state.stats.totals.longest_phase_pokemon, true))
            document.getElementById("longest_phase_encounters").innerText = state.stats.totals.longest_phase_encounters.toLocaleString()
            $("#shortest_phase_sprite").attr("src", pokemonSprite(state.stats.totals.shortest_phase_pokemon, true))
            document.getElementById("shortest_phase_encounters").innerText = state.stats.totals.shortest_phase_encounters.toLocaleString()
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

    $("#encounter_log").prepend(
        $("<tr>")
            .append($("<td>")
                .append($("<div>")
                    .append($("<img>")
                        .addClass("sprite")
                        .attr({ "src": pokemonSprite(data.species.name, data.is_shiny, false) }))
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

    $("#encounter_log").children().slice(8).detach()
}

function refreshShinyLog() {
    fetch("/shiny_log?limit=9")
        .then(response => response.json())
        .then(data => {
            $("#shiny_log").empty()

            state.shiny_log = data

            for (var i = 0; i < 8; i++) {
                if (typeof data[i] === "undefined") {
                    $("#shiny_log").append($("<tr>")
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
                    if (data[i + 1]) {
                        a = moment.unix((Math.round(data[i].time_encountered)))
                        b = moment.unix((Math.round(data[i + 1].time_encountered)))
                        delta = a.diff(b, "hours", true)

                        if (delta < 1) {
                            delta = a.diff(b, "minutes", true).toPrecision(2).toLocaleString()
                            delta_unit = "min"
                        } else {
                            delta = delta.toPrecision(2).toLocaleString()
                            delta_unit = "hr"
                        }
                    } else {
                        delta = "-"
                        delta_unit = ""
                    }

                    $("#shiny_log").append($("<tr>")
                        .append($("<td>")
                            .append($("<img>")
                                .addClass("sprite")
                                .attr({ "src": pokemonSprite(data[i].pokemon.name, true, false) })))
                        .append($("<td>")
                            .addClass("sv_yellow")
                            .text(data[i].pokemon.shinyValue))
                        .append($("<td>")
                            .text(data[i].snapshot_stats.phase_encounters.toLocaleString()))
                        .append($("<td>")
                            .css({ "font-size": "1.333rem" })
                            .text(delta)
                            .append($("<span>")
                                .css({ "font-size": "1rem" })
                                .text(" " + delta_unit)))
                        .append($("<td>")
                            .css({ "font-size": "1.333rem" })
                            .text(calcPSP(data[i].snapshot_stats.phase_encounters).toPrecision(3).toString() + "%"))
                        .append($("<td>")
                            .text(intShortName(data[i].snapshot_stats.species_encounters, 3)))
                        .append($("<td>")
                            .text(data[i].snapshot_stats.species_shiny_encounters.toLocaleString()))
                        .append($("<td>")
                            .text(intShortName(data[i].snapshot_stats.total_encounters, 3)))
                    )
                }
            }
        })
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

function refreshchecklist() {
    $("#checklist").empty()

    if (state.stats === null) {
        return
    }

    // Get encounter rates for the current map + bot mode
    if (["Spin", "Sweet Scent"].includes(state.bot_mode)) {
        if (state.map.tiles[state.map.player_position[0]][state.map.player_position[1]].is_surfing_possible) {
            encounters = state.map.encounters.surf_encounters
        } else {
            encounters = state.map.encounters.land_encounters
        }
    } else if (["Fishing", "Feebas"].includes(state.bot_mode)) {
        if (state.player.registered_item === "Super Rod") {
            encounters = state.map.encounters.super_rod_encounters
        } else if (state.player.registered_item === "Good Rod") {
            encounters = state.map.encounters.good_rod_encounters
        } else {
            encounters = state.map.encounters.old_rod_encounters
        }
    } else if (state.bot_mode === "Rock Smash") {
        encounters = state.map.encounters.rock_smash_encounters
    } else {
        encounters = state.map.encounters.land_encounters
    }

    mode_encounters = {}
    route_checklist = {}
    encounters.forEach(encounter => {
        if (mode_encounters[encounter.species]) {
            mode_encounters[encounter.species] += encounter.encounter_rate
        } else {
            mode_encounters[encounter.species] = encounter.encounter_rate
        }

        if (!pokemon_checklist[encounter.species]) {
            route_checklist[encounter.species] = {
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
            checklist_mon.phase_encounters = (state.stats.pokemon[name].phase_encounters != null) ? state.stats.pokemon[name].phase_encounters : 0
            checklist_mon.encounters = (state.stats.pokemon[name].encounters != null) ? state.stats.pokemon[name].encounters : 0
            checklist_mon.phase_lowest_sv = (state.stats.pokemon[name].phase_lowest_sv != null) ? state.stats.pokemon[name].phase_lowest_sv : 99999
            checklist_mon.phase_highest_sv = (state.stats.pokemon[name].phase_highest_sv != null) ? state.stats.pokemon[name].phase_highest_sv : 99999
            checklist_mon.phase_highest_iv_sum = (state.stats.pokemon[name].phase_highest_iv_sum != null) ? state.stats.pokemon[name].phase_highest_iv_sum : 99999
            checklist_mon.phase_lowest_iv_sum = (state.stats.pokemon[name].phase_lowest_iv_sum != null) ? state.stats.pokemon[name].phase_lowest_iv_sum : 99999
            checklist_mon.phase_percent = (state.stats.pokemon[name].phase_encounters > 0) ? ((state.stats.pokemon[name].phase_encounters / state.stats.totals.phase_encounters) * 100).toPrecision(4) + "%" : ""
    
            if (state.stats.pokemon[name].shiny_average) {
                checklist_mon.shiny_average = "(" + state.stats.pokemon[name].shiny_average + ")"
            } else {
                checklist_mon.shiny_average = ""
            }
        }

        checklist_required_mons += obj.goal
        checklist_progress += Math.min(obj.goal, checklist_mon.shiny_encounters)

        if (!obj.hidden){
            animated_sprite = false
            if (state.opponent.species.name === name){
                animated_sprite = true
            }
    
            $("#checklist").append($("<tr>")
                .addClass("checklist")
                .append($("<td>")
                    .append($("<img>")
                        .addClass("checklist-sprite")
                        .attr({ "src": pokemonSprite(name, true, animated_sprite) })))
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
                    .text(checklist_mon.shiny_encounters.toLocaleString())
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
                        .attr({ "src": (!obj.goal || checklist_mon.shiny_encounters >= obj.goal) ? "sprites/stream-overlay/tick.png" : "sprites/items/None.png" })))
            )
        }
    }

    checklist_percent = (checklist_progress / checklist_required_mons) * 100
    $("#progress_bar_fill").css("width", checklist_percent + "%")
    if (checklist_percent === 100){
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

    var time = new Date()
    $("#local_time").html(time.toLocaleString("en-US", {
        hour: "numeric",
        minute: "numeric",
        second: "numeric",
        hour12: true
    }) + ' <span style="font-size: 1.2rem;">' + getAbbreviation(Intl.DateTimeFormat().resolvedOptions().timeZone) + "</span>")

    if (state.opponent !== null) {
        if (state.opponent.is_shiny && state.opponent.personality_value != state.shiny_log[0].pokemon.pid) {
            // TEMP/hacky way to ensure shiny log is updated when current opponent is shiny
            refreshShinyLog()

            fetch("/stats")
            .then(response => response.json())
            .then(data => {
                handleStats(data)
            })
        } else if (state.shiny_log[0] !== undefined && !state.opponent.is_shiny) {
            // Don't update phase time on shinies (for OBS screenshot)
            $("#phase_time_hrs").text((diffDays(state.shiny_log[0].time_encountered * 1000) * 24) + (diffHrs(state.shiny_log[0].time_encountered * 1000)))
            $("#phase_time_mins").text(diffMins((state.shiny_log[0].time_encountered * 1000)))
        }
    }

    if (state.stats !== null) {
        if (target_timer_1 !== "" && state.stats.pokemon[target_timer_1] !== undefined) {
            var target_date = new Date(state.stats.pokemon[target_timer_1].last_encounter_time_unix * 1000)
            target_timer_hrs = diffHrs(target_date).toLocaleString()
            target_timer_mins = diffMins(target_date).toLocaleString()
            $("#target_1_timer_hrs").text(target_timer_hrs)
            $("#target_1_timer_mins").text(target_timer_mins)
        }

        if (target_timer_2 !== "" && state.stats.pokemon[target_timer_2] !== undefined) {
            var target_date = new Date(state.stats.pokemon[target_timer_2].last_encounter_time_unix * 1000)
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

function pokemonSprite(name, shiny, animated) {
    if (animated) {
        if (shiny) {
            return "sprites/pokemon-animated/shiny/" + name + ".gif"
        }

        return "sprites/pokemon-animated/normal/" + name + ".gif"
    }

    if (shiny) {
        return "sprites/pokemon/shiny/" + name + ".png"
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

moment.updateLocale("en", {
    relativeTime: {
        future: "%s",
        past: "%s",
        s: "%d s",
        ss: "%d s",
        m: "%d m",
        mm: "%d m",
        h: "%d h",
        hh: "%d h",
        d: "%d d",
        dd: "%d d",
        w: "%d w",
        ww: "%d w",
        M: "%d mo",
        MM: "%d mo",
        y: "%d y",
        yy: "%d y"
    }
})

var retainValue = function (value) {
    return Math.floor(value)
}

moment.relativeTimeRounding(retainValue)

function clamp(number, min, max) {
    return Math.max(min, Math.min(number, max))
}

function diffMs(time) {
    var now = new Date()
    var start = new Date(time)
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

function getAbbreviation(tz) {
    return getFormattedElement(tz, "timeZoneName", "short")
}

function getFormattedElement(tz, name, value) {
    if (override_display_timezone === "") {
        return (new Intl.DateTimeFormat('en', {
            [name]: value,
            tz
        }).formatToParts().find(el => el.type === name) || {}).value
    } else {
        return override_display_timezone
    }
}

function intShortName(number, precision) {
    return Math.abs(Number(number)) >= 1.0e+9
        ? (Math.abs(Number(number)) / 1.0e+9).toFixed(precision) + "B"
        : Math.abs(Number(number)) >= 1.0e+6
            ? (Math.abs(Number(number)) / 1.0e+6).toFixed(precision) + "M"
            : Math.abs(Number(number)).toLocaleString();
}