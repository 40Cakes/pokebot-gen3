export default class ShinyValue extends HTMLSpanElement {
    static observedAttributes = ["value"];

    constructor() {
        super();
        self.value = null;
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "value") {
            self.value = newValue;

            if (typeof self.value === "string") {
                self.value = Number.parseFloat(self.value);
            }

            if (typeof self.value === "number") {
                self.innerText = self.value.toLocaleString("en");
                self.style.display = "inline";

                if (self.value < 8) {
                    self.classList.add("text-yellow");
                    self.classList.remove("text-purple");
                    self.classList.remove("text-red");
                } else if (self.value > 65527) {
                    self.classList.remove("text-yellow");
                    self.classList.add("text-purple");
                    self.classList.remove("text-red");
                } else {
                    self.classList.remove("text-yellow");
                    self.classList.remove("text-purple");
                    self.classList.add("text-red");
                }
            } else {
                self.style.display = "none";
            }
        }
    }
}
