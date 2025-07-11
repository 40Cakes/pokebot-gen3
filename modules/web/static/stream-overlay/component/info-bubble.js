import {formatInteger} from "../helper.js";

export default class InfoBubble extends HTMLElement {
    static observedAttributes = ["sprite-location", "sprite-type", "sprite-icon", "quantity", "quantity-target", "content"];

    constructor() {
        super();

        /** @type {HTMLImageElement | PokemonSprite | ItemSprite | OverlaySprite | null} */
        this.sprite = null;

        /** @type {"item" | "pokemon" | "shiny-pokemon" | "anti-pokemon" | "overlay" | null} */
        this.spriteType = null;

        /** @type {string | null} */
        this.spriteIcon = null;

        /** @type {number | null} */
        this.updateInterval = null;

        /** @type {HTMLSpanElement | null} */
        this.content = null;

        /** @type {number | null} */
        this.quantity = null;

        /** @type {number | null} */
        this.quantityTarget = null;
    }

    connectedCallback() {
        this.spriteType = this.getAttribute("sprite-type");
        this.spriteIcon = this.getAttribute("sprite-icon");
        this.content = this.querySelector("span");
        if (this.content === null) {
            this.content = document.createElement("span");
            this.append(this.content);
        }
        if (this.hasAttribute("quantity")) {
            const quantity = Number.parseInt(this.getAttribute("quantity"));
            if (!isNaN(quantity)) {
                this.content.innerText = formatInteger(quantity);
            }
        } else if (this.hasAttribute("content")) {
            this.content.innerText = this.getAttribute("content");
        }
        this.updateSprite();
        this.updateCounter();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "sprite-location") {
            if (newValue === "right") {
                self.classList.add("sprite-right");
            } else {
                self.classList.remove("sprite-right");
            }
        }

        let spriteNeedsUpdating = false;

        if (name === "sprite-type") {
            this.spriteType = newValue;
            if (this.spriteType && this.spriteIcon) {
                spriteNeedsUpdating = true;
            }
        }

        if (name === "sprite-icon") {
            this.spriteIcon = newValue;
            if (this.spriteType && this.spriteIcon) {
                spriteNeedsUpdating = true;
            }
        }

        if (name === "quantity") {
            const newQuantity = Number.parseInt(newValue);
            if (!isNaN(newQuantity)) {
                this.quantity = newQuantity;
                this.updateCounter();
            } else {
                this.quantity = null;
            }
        }

        if (name === "quantity-target") {
            const newTarget = Number.parseInt(newValue);
            let small = this.querySelector("small");
            if (!isNaN(newTarget) && newTarget > 0) {
                this.quantityTarget = newTarget;
                if (!small) {
                    small = document.createElement("small");
                    this.append(small);
                }
                small.innerText = "/" + formatInteger(newValue)
            } else if (small) {
                this.quantityTarget = null;
                small.remove();
            }
        }

        if (name === "content") {
            this.content.innerText = newValue;
        }

        if (spriteNeedsUpdating) {
            this.updateSprite();
        }
    }

    updateSprite() {
        if (this.sprite) {
            this.sprite.remove();
            this.sprite = null;
        }

        if (this.spriteType === "item") {
            this.sprite = document.createElement("item-sprite");
            this.sprite.setAttribute("item", this.spriteIcon);
        } else if (this.spriteType === "overlay") {
            this.sprite = document.createElement("overlay-sprite");
            this.sprite.setAttribute("icon", this.spriteIcon);
        } else if (this.spriteType === "pokemon") {
            this.sprite = document.createElement("pokemon-sprite");
            this.sprite.setAttribute("species", this.spriteIcon);
        } else if (this.spriteType === "shiny-pokemon") {
            this.sprite = document.createElement("pokemon-sprite");
            this.sprite.setAttribute("species", this.spriteIcon);
            this.sprite.setAttribute("shiny", "shiny");
        } else if (this.spriteType === "anti-pokemon") {
            this.sprite = document.createElement("pokemon-sprite");
            this.sprite.setAttribute("species", this.spriteIcon);
            this.sprite.setAttribute("shiny", "anti");
        }

        if (this.sprite) {
            this.prepend(this.sprite);
        }
    }

    updateCounter() {
        if (this.updateInterval) {
            window.clearInterval(this.updateInterval);
            this.updateInterval = null;
        }

        if (!this.quantity) {
            return;
        }

        let currentCounter = Number.parseInt(this.content.innerText);
        if (isNaN(currentCounter) || this.content.innerText === "") {
            this.content.innerText = formatInteger(this.quantity);
            return;
        }

        const diff = Math.abs(this.quantity - currentCounter);
        const sign = Math.sign(this.quantity - currentCounter);

        if (diff === 0) {
            return;
        }

        let increasePerStep = Math.floor(diff / 12);
        let intervalLength = 250;
        let intervalsLeft = 12;
        if (diff <= 6) {
            increasePerStep = 1;
            intervalLength = 500;
            intervalsLeft = diff;
        } else if (increasePerStep === 0) {
            increasePerStep = 1;
            intervalLength = Math.floor(3000 / diff);
            intervalsLeft = diff;
        }

        const quantityTarget = Number.parseInt(this.getAttribute("quantity-target"));

        this.updateInterval = window.setInterval(
            () => {
                if (intervalsLeft <= 1) {
                    this.content.innerText = formatInteger(this.quantity);
                    window.clearInterval(this.updateInterval);
                    this.updateInterval = null;
                } else {
                    currentCounter += sign * increasePerStep;
                    this.content.innerText = formatInteger(currentCounter);
                }
                if (quantityTarget && !isNaN(quantityTarget)) {
                    let small = this.querySelector("small");
                    if (!small) {
                        small = document.createElement("small");
                        this.append(small);
                    }
                    small.innerText = "/" + formatInteger(quantityTarget);
                }
                intervalsLeft--;
            },
            intervalLength);
    }
}
