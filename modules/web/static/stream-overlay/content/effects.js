function fireConfetti(booms, durationInSections) {
    let remaining = booms;
    const maxDelay = Math.round(1000 * 2 * durationInSections / booms);

    const fireOneConfetti = () => {
        let x, y;
        do {
            x = Math.floor(Math.random() * 100);
            y = Math.floor(Math.random() * 100);
        } while (x < 57 && y < 66);

        try {
            confetti({position: {x, y}});

            if (--remaining > 0) {
                window.setTimeout(() => fireOneConfetti(), Math.floor(Math.random() * maxDelay));
            }
        } catch (error) {
            console.error(error);
        }
    };

    if (typeof window.confetti === "function") {
        fireOneConfetti();
    }
}

function fireWaterBubbleBurst() {
    const spawnBubbles = (n) => {
        const viewpointWidth = window.innerWidth;

        let elements = [];
        for (let index = 0; index < n; index++) {
            const element = document.createElement("div");
            element.className = "water-bubble";

            const width = Math.round(Math.random() * 7 + 3);
            const diameter = width * 7 + 2;
            element.style.fontSize = `${width}px`;
            element.style.left = Math.round(Math.random() * viewpointWidth - diameter / 2) + "px";
            element.style.bottom = `-${diameter + Math.round(Math.random() * 500)}px`;
            element.style.animationDuration = `${Math.round(Math.random() * 1000 + 500)}ms`;

            document.body.appendChild(element);
            elements.push(element);
        }

        window.setTimeout(() => elements.forEach(element => document.body.removeChild(element)), 2500);
    }

    window.setTimeout(() => spawnBubbles(35), 100);
    window.setTimeout(() => spawnBubbles(45), 250);
    window.setTimeout(() => spawnBubbles(55), 500);
}

export {fireConfetti, fireWaterBubbleBurst};
