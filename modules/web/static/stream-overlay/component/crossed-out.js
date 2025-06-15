export default class CrossedOut extends HTMLElement {
    constructor() {
        super();

        /** @type {HTMLImageElement | null} */
        this.crossSprite = null;
    }

    connectedCallback() {
        this.style.position = "relative";

        if (!this.crossSprite) {
            this.crossSprite = document.createElement("img");
            this.crossSprite.setAttribute("src", "../sprites/stream-overlay/cross.png");
            this.crossSprite.alt = "Crossed out";
            this.crossSprite.style.position = "absolute";
            this.crossSprite.style.bottom = "0";
            this.crossSprite.style.right = "0";
            this.crossSprite.style.height = "40%";
            this.append(this.crossSprite);
        }
    }

    disconnectedCallback() {
        if (this.crossSprite) {
            this.crossSprite.remove();
            this.crossSprite = null;
        }
    }
}
