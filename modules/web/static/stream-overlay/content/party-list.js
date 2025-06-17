import {eggSprite, speciesSprite} from "../helper.js";

const ul = document.querySelector("#party-list ul")

/**
 * @param {PokeBotApi.GetPartyResponse} party
 */
function updatePartyList(party) {
    ul.innerHTML = "";

    for (const member of party) {
        const li = document.createElement("li");

        let hpPercentage = Math.round(100 * member.current_hp / member.total_hp);
        let expPercentage = Math.round(100 * member.exp_fraction_to_next_level);

        let sprite;
        if (member.is_egg) {
            sprite = eggSprite(true);
            hpPercentage = 0;
            expPercentage = Math.round(100 * (member.species.egg_cycles - member.friendship) / member.species.egg_cycles);
        } else if (member.current_hp === 0) {
            sprite = speciesSprite(member.species_name_for_stats, member.is_shiny ? "shiny" : "normal", false);
            sprite.classList.add("fainted");
        } else {
            sprite = speciesSprite(member.species_name_for_stats, member.is_shiny ? "shiny" : "normal", true);
        }

        let statusCondition = "";
        if (member.current_hp === 0 || member.status_condition !== "Healthy") {
            statusCondition = document.createElement("img");
            statusCondition.classList.add("status-condition");
            if (member.current_hp === 0) {
                statusCondition.src = "/static/sprites/status/fainted.png";
            } else if (member.status_condition === "Sleep") {
                statusCondition.src = "/static/sprites/status/asleep.png";
            } else if (member.status_condition === "Burn") {
                statusCondition.src = "/static/sprites/status/burned.png";
            } else if (member.status_condition === "Freeze") {
                statusCondition.src = "/static/sprites/status/frozen.png";
            } else if (member.status_condition === "Paralysis") {
                statusCondition.src = "/static/sprites/status/paralysed.png";
            } else {
                statusCondition.src = "/static/sprites/status/poisoned.png";
            }
        }

        const healthBar = document.createElement("div");
        healthBar.classList.add("health-bar");
        healthBar.style.width = `${hpPercentage}%`;
        if (hpPercentage >= 50) {
            healthBar.classList.add("green");
        } else if (hpPercentage >= 10) {
            healthBar.classList.add("yellow");
        } else {
            healthBar.classList.add("red");
        }

        const expBar = document.createElement("div");
        expBar.classList.add("exp-bar");
        expBar.style.width = `${expPercentage}%`;

        li.append(sprite);
        li.append(statusCondition);
        li.append(healthBar);
        li.append(expBar);

        if (member.held_item) {
            const heldItem = document.createElement("img");
            heldItem.src = `../sprites/items/${member.held_item.name}.png`;
            heldItem.classList.add("held-item");
            li.append(heldItem);
        }

        ul.append(li);
    }

    for (let index = party.length; index < 6; index++) {
        ul.append(document.createElement("li"));
    }
}

export {updatePartyList};
