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

export {fireConfetti};
