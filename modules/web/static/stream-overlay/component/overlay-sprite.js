export default class OverlaySprite extends HTMLElement {
    static observedAttributes = ["icon"];

    constructor() {
        super();

        /** @type {HTMLImageElement | null} */
        this.sprite = null;
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "icon") {
            if (newValue) {
                const src = `../sprites/stream-overlay/${encodeURIComponent(newValue)}.png`;
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
