/** @type {HTMLDivElement} */
const safariRatesBox = document.getElementById("safari-rates");

const sectionChecklistBox = document.getElementById("section-checklist");

/** @type {HTMLSpanElement} */
const safariCatchRateLabel = document.getElementById("safari_catch_rate");
/** @type {HTMLSpanElement} */
const safariEscapeRateLabel = document.getElementById("safari_escape_rate");

/**
 * @param {number|null} catchRate
 * @param {number|null} escapeRate
 */
const showSafariRates = (catchRate, escapeRate) => {
    if (catchRate === null || escapeRate === null) {
        hideSafariRates();
        return;
    }

    safariCatchRateLabel.innerText = (catchRate * 100).toFixed(1) + "%";
    safariEscapeRateLabel.innerText = (100 * escapeRate).toFixed(0) + "%";

    safariRatesBox.style.display = "block";
    sectionChecklistBox.style.display = "none";
}

const hideSafariRates = () => {
    safariRatesBox.style.display = "none";
    sectionChecklistBox.style.display = "block";
}


export {showSafariRates};
