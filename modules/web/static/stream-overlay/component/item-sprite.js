export default class ItemSprite extends HTMLElement {
    static observedAttributes = ["item"];

    constructor() {
        super();

        /** @type {HTMLImageElement | null} */
        this.sprite = null;
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "item") {
            if (newValue) {
                const src = `../sprites/items/${encodeURIComponent(newValue)}.png`;
                if (!this.sprite) {
                    this.sprite = document.createElement("img");
                    this.append(this.sprite);
                }

                if (this.sprite.src !== src) {
                    this.sprite.src = src;
                    this.sprite.alt = newValue;
                }
            } else if (this.sprite) {
                this.sprite.remove();
                this.sprite = null;
            }
        }
    }
}
