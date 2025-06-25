import {calculatePSP, diffHoursMinutes, formatInteger, formatRecords, speciesSprite} from "../helper.js";

const phaseTimer = document.querySelector("#phase-timer-stat");
const phaseEncounters = document.querySelector("#phase-encounters-stat");
const psp = document.querySelector("#psp-stat");
const longestStreak = document.querySelector("#phase-streak-stat");
const phaseIVSumRecords = document.querySelector("#phase-iv-sum-records-stat");

/**
 * @param {PokeBotApi.GetStatsResponse} stats
 */
function updatePhaseStats(stats) {
    const currentPhase = stats.current_phase;

    phaseTimer.innerHTML = diffHoursMinutes(new Date(currentPhase.start_time).getTime());
    phaseEncounters.innerText = formatInteger(currentPhase.encounters);
    psp.innerText = calculatePSP(currentPhase.encounters);

    longestStreak.innerHTML = "";
    if (currentPhase.longest_streak?.species_name) {
        const sprite = speciesSprite(currentPhase.longest_streak.species_name);
        longestStreak.append(sprite);
        longestStreak.append(currentPhase.longest_streak.value.toLocaleString("en") + " ");

        if (currentPhase.current_streak?.species_name) {
            const currentStreakNumber = document.createElement("small");
            currentStreakNumber.innerText = `(${currentPhase.current_streak.value.toLocaleString("en")})`;
            longestStreak.append(currentStreakNumber);
        }
    }

    phaseIVSumRecords.innerHTML = "";
    if (currentPhase.highest_iv_sum?.species_name && currentPhase.lowest_iv_sum?.species_name) {
        phaseIVSumRecords.append(...formatRecords(currentPhase.highest_iv_sum, currentPhase.lowest_iv_sum));
    }
}

export {updatePhaseStats};
