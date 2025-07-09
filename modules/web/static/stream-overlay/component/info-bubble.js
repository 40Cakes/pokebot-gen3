export default class InfoBubble extends HTMLDivElement {
    static observedAttributes = ["sprite-location"];

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "sprite-location") {
            if (newValue === "right") {
                self.classList.add("sprite-right");
            } else {
                self.classList.remove("sprite-right");
            }
        }
    }
}
