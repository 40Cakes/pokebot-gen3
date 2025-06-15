const div = document.querySelector("div#badge-list");

/**
 * @param {string} game
 * @param {PokeBotApi.GetEventFlagsResponse} eventFlags
 */
function updateBadgeList(game, eventFlags) {
    let badgeNames = [];
    if (["RUBY", "SAPP", "EMER"].includes(game.slice(8))) {
        badgeNames = ["Stone", "Knuckle", "Dynamo", "Heat", "Balance", "Feather", "Mind", "Rain"];
    } else if (["FIRE", "LEAF"].includes(game.slice(8))) {
        badgeNames = ["Boulder", "Cascade", "Thunder", "Rainbow", "Soul", "Marsh", "Volcano", "Earth"];
    }

    div.innerHTML = "";

    for (let index = 0; index < badgeNames.length; index++) {
        const badgeName = badgeNames[index];

        const img = document.createElement("img");
        img.src = `/static/sprites/badges/${badgeName}.png`;
        img.alt = `${badgeName} Badge`;

        if (!eventFlags[`BADGE0${index + 1}_GET`]) {
            img.classList.add("unobtained");
        }

        div.append(img);
    }
}

export {updateBadgeList};
