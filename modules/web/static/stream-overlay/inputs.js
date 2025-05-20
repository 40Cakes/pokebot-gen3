const buttonArrowUp = document.querySelector("#arrow-up");
const buttonArrowRight = document.querySelector("#arrow-right");
const buttonArrowDown = document.querySelector("#arrow-down");
const buttonArrowLeft = document.querySelector("#arrow-left");
const buttonA = document.querySelector("#svg-a");
const buttonB = document.querySelector("#svg-b");
const buttonSelect = document.querySelector("#svg-select");
const buttonStart = document.querySelector("#svg-start");

const notPressedOpacity = "0.15";
const pressedOpacity = ".9";

/**
 * @param {StreamEvents.Inputs} inputs
 */
function updateInputs(inputs) {
    buttonArrowUp.style.opacity = inputs.includes("Up") ? pressedOpacity : notPressedOpacity;
    buttonArrowRight.style.opacity = inputs.includes("Right") ? pressedOpacity : notPressedOpacity;
    buttonArrowDown.style.opacity = inputs.includes("Down") ? pressedOpacity : notPressedOpacity;
    buttonArrowLeft.style.opacity = inputs.includes("Left") ? pressedOpacity : notPressedOpacity;
    buttonA.style.opacity = inputs.includes("A") ? pressedOpacity : notPressedOpacity;
    buttonB.style.opacity = inputs.includes("B") ? pressedOpacity : notPressedOpacity;
    buttonSelect.style.opacity = inputs.includes("Select") ? pressedOpacity : notPressedOpacity;
    buttonStart.style.opacity = inputs.includes("Start") ? pressedOpacity : notPressedOpacity;
}

export {updateInputs};
