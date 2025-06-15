export default class IV extends HTMLSpanElement {
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

                const classes = {
                    "yellow": self.value === 31,
                    "green": self.value >= 26 && self.value < 31,
                    "white": self.value >= 6 && self.value < 26,
                    "red": self.value >= 1 && self.value < 6,
                    "purple": self.value === 0,
                };

                for (const [className, isActive] of Object.entries(classes)) {
                    if (isActive) {
                        self.classList.add(className);
                    } else {
                        self.classList.remove(className);
                    }
                }
            } else {
                self.style.display = "none";
            }
        }
    }
}
