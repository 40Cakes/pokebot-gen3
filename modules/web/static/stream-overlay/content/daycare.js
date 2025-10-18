import {colouredIV, speciesSprite} from "../helper.js";
import {fetchers} from "../connection.js";

const DAYCARE_UPDATE_INTERVAL = 10000;

/** @type {HTMLDivElement} */
const daycareInfoBox = document.getElementById("daycare-info");
/** @type {HTMLUListElement} */
const daycareInfoList = document.querySelector("#daycare-info > ul");

let daycareBoxIsVisible = false;

let daycareUpdateTimer = null;

/**
 * @param {string} botMode
 * @param {OverlayState} state
 */
const updateDaycareBox = (botMode, state) => {
    const isInDaycareMode = state.daycareMode || botMode.toLowerCase().includes("daycare");

    if (isInDaycareMode && !daycareBoxIsVisible) {
        daycareInfoBox.style.display = "block";
        daycareBoxIsVisible = true;
    } else if (!isInDaycareMode && daycareBoxIsVisible) {
        daycareInfoBox.style.display = "none";
        if (daycareUpdateTimer) {
            window.clearInterval(daycareUpdateTimer);
            daycareUpdateTimer = null;
        }
        daycareBoxIsVisible = false;
        return;
    } else if (!isInDaycareMode) {
        return;
    }

    if (!daycareUpdateTimer) {
        daycareUpdateTimer = window.setInterval(
            () => {
                fetchers.daycare().then(newData => {
                    state.daycare = newData;
                    updateDaycareBox(botMode, state);
                });
            },
            DAYCARE_UPDATE_INTERVAL);
    }

    daycareInfoList.innerHTML = "";

    /**
     * @param {Pokemon} pokemon
     * @param {number} newLevel
     * @returns {HTMLLIElement}
     */
    const createPokemonBox = (pokemon, newLevel) => {
        const li = document.createElement("li");

        const sprite = speciesSprite(pokemon.species.name, pokemon.is_shiny ? "shiny-cropped" : "normal-cropped");
        li.append(sprite);

        if (pokemon.gender === "male" || pokemon.gender === "female") {
            const genderIcon = document.createElement("img");
            genderIcon.classList.add("gender-icon");
            if (pokemon.gender === "male") {
                genderIcon.src = "/static/sprites/other/Male.png";
                genderIcon.alt = "Male";
            } else {
                genderIcon.src = "/static/sprites/other/Female.png";
                genderIcon.alt = "Feale";
            }
            li.append(genderIcon);
        }

        const speciesName = document.createElement("div");
        speciesName.innerText = pokemon.species.name;
        li.append(speciesName);

        const level = document.createElement("div");
        const levelLabel = document.createElement("small");
        levelLabel.innerText = "Level: ";
        level.innerText = newLevel.toString();
        level.prepend(levelLabel);
        li.append(level);

        const slash = () => {
            const element = document.createElement("small");
            element.innerText = "/";
            return element;
        }
        const ivs = document.createElement("div");
        ivs.className = "daycare-ivs";
        const ivsLabel = document.createElement("small");
        ivsLabel.innerText = "IVs: ";
        ivs.append(
            ivsLabel,
            colouredIV(pokemon.ivs.hp),
            slash(),
            colouredIV(pokemon.ivs.attack),
            slash(),
            colouredIV(pokemon.ivs.defence),
            slash(),
            colouredIV(pokemon.ivs.special_attack),
            slash(),
            colouredIV(pokemon.ivs.special_defence),
            "/",
            colouredIV(pokemon.ivs.speed),
        );
        li.append(ivs);

        const heldItem = document.createElement("div");
        const heldItemLabel = document.createElement("small");
        heldItemLabel.innerText = "Held Item: ";
        heldItem.innerText = pokemon.held_item ? pokemon.held_item.name : "None";
        heldItem.prepend(heldItemLabel);
        li.append(heldItem);

        return li;
    };

    if (state.daycare.pokemon1 !== null) {
        daycareInfoList.append(createPokemonBox(state.daycare.pokemon1, state.daycare.pokemon1_new_level));
    }

    if (state.daycare.pokemon2 !== null) {
        daycareInfoList.append(createPokemonBox(state.daycare.pokemon2, state.daycare.pokemon2_new_level));
    }
};

export {updateDaycareBox};
