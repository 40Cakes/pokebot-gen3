const buttonElements = {
    "Up": document.querySelector("#arrow-up"),
    "Right": document.querySelector("#arrow-right"),
    "Down": document.querySelector("#arrow-down"),
    "Left": document.querySelector("#arrow-left"),

    "A": document.querySelector("#button-a"),
    "B": document.querySelector("#button-b"),
    "Start": document.querySelector("#button-start"),
    "Select": document.querySelector("#button-select"),
};

/**
 * @param {StreamEvents.Inputs} inputs
 */
function updateInputs(inputs) {
    for (const button in buttonElements) {
        if (inputs.includes(button)) {
            buttonElements[button].classList.add("pressed");
        } else {
            buttonElements[button].classList.remove("pressed");
        }
    }
}

export {updateInputs};
