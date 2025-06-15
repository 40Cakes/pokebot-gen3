import {small} from "../helper.js";

/** @type {Intl.DateTimeFormat} */
let dateFormatter;

const timeOfDay = document.querySelector("#time-of-day");
const runtime = document.querySelector("#runtime");

/**
 * @param {string} startDate
 * @param {string | null} timeZone
 * @param {string | null} overrideDisplayTimezone
 */
function updateClock(startDate, timeZone = null, overrideDisplayTimezone = null) {
    if (!dateFormatter) {
        dateFormatter = Intl.DateTimeFormat("en", {
            hour: "numeric",
            minute: "numeric",
            second: "numeric",
            hour12: true,
            timeZone: timeZone,
        });
    }

    timeOfDay.textContent = dateFormatter.format(new Date());
    if (overrideDisplayTimezone) {
        timeOfDay.append(small(" " + overrideDisplayTimezone));
    }

    const runtimeInHours = (new Date().getTime() - new Date(startDate).getTime()) / (1000 * 3600);
    runtime.textContent = "";
    runtime.append(
        Math.floor(runtimeInHours / 24),
        small(" days, "),
        Math.floor(runtimeInHours % 24),
        small(" hours"),
    );
}

export {updateClock};
