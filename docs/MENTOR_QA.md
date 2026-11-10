# Mentor Q&A — questions we should expect, and our answers

> Everyone on the team should be able to answer these in their own words. Numbers come from the app, not from this file.

## Modelling

**1. Why not a random train/test split?**
Solar data is a time series. Neighbouring 15-minute rows are almost identical, so a random split lets the model "see" the test period through its neighbours and scores look perfect. Our problem statement asks for unseen time periods, so we split by consecutive days and also run rolling-origin evaluation.

**2. Why don't you use DC_POWER as an input? It would give R2 near 1.**
DC power is part of the output chain. AC is DC converted by the inverter, so using DC would re-state the target and hide the very deviations we want to find. We use DC separately to check conversion consistency (DC-to-AC ratio), which is evidence for or against an inverter-related explanation.

**3. Why no inverter id as a feature?**
With the id, the model would learn that a weak inverter normally produces less, and the deviation would disappear. Without it, the model predicts what a typical inverter should do under the same weather. All inverters in a plant share one weather sensor, so comparing against peers cancels the weather.

**4. Why per-plant models?**
The plants differ in size and reporting (for example DC scaling). One model per plant avoids mixing those differences into the weather relationship.

**5. Which models did you compare and why?**
A previous-day persistence reference, a physics-based formula (`P = a G (1 + gamma (T - 25))`), a polynomial ridge regression, a random forest, and gradient boosting with a monotonic constraint on irradiation. They range from simple and explainable to flexible. We choose by validation daylight RMSE and prefer the simpler model when it is within 3%.

**6. Why daylight-only metrics?**
Night rows are zero and easy to predict, which inflates R2. We show both, but the daylight numbers are the honest ones.

**7. Isn't 34 days too little data?**
It is limited, so we keep models modest, avoid heavy tuning, and state that results apply to this period. We show stability across rolling folds and clear versus cloudy days instead of one headline number.

**8. Did you tune on the test set?**
No. Tuning uses walk-forward folds inside the training block; selection uses the validation block; the test block is reported once.

## Anomaly detection

**9. How do you decide what is "significantly different"?**
We build a prediction band from validation residuals (split-conformal, 99% coverage, wider at higher power) and flag points outside it. A deviation must persist for at least 3 consecutive intervals (45 minutes) to become an event, which removes isolated noise.

**10. Are those anomalies equipment faults?**
No, and the product never says so. We have no maintenance logs, alarms or inspection reports. Each event gets a category (data quality, weather transient, fleet-wide, inverter-specific, unexplained), a confidence based on independent signals, and a list of external evidence that would confirm it. The strongest statement we make is "inverter below its peers for N intervals: candidate for inspection".

**11. How do you know your detector works without labels?**
We inject known deviations (drops of 10/20/40%, spikes, flat-lines) into the unseen test period and measure recall, precision and detection delay. The drop sweep gives the smallest deviation we can reliably detect. We also compare the flag rate on validation and test as a stability check.

**12. What about a cloud that passes over only part of the plant?**
One plant-level sensor cannot see it, so the model can mismatch for a short time. We mark such events as weather transient when irradiation volatility is high, and fleet-wide behaviour (many inverters moving together) supports that interpretation.

**13. Could the sensor be wrong rather than the plant?**
Yes. That is why data-quality checks (gaps, flat-lines, night power, negative values, AC/DC consistency) run first and take priority in the category order. Those events are excluded from the monetary claim and shown as a separate amount.

**14. Can you detect soiling?**
Not directly. There is no rainfall or cleaning data and only 34 days. We can show a Performance Index trend and say "possible soiling, needs cleaning and rain records".

## Financial

**15. Where does the tariff come from?**
It is a configurable assumption (see `DECISION_LOG.md` D-009), with a sensitivity table. The estimate is for the dataset period only and not an annual forecast.

**16. Why three numbers (conservative, central, upper)?**
Because the model has uncertainty and some deviations may be measurement problems. Conservative counts only the part beyond the normal band; central is the difference from prediction in non-data-quality events; upper adds data-quality events as if the readings were true. Surplus is shown separately and never subtracts from shortfall.

## Engineering and product

**17. Why FastAPI and vanilla JavaScript?**
FastAPI gives typed, documented REST endpoints and works directly with our Python ML code. Vanilla JavaScript plus Chart.js keeps the frontend simple for a four-person team and uses the Fetch API as required.

**18. Why no database?**
The data is small (a few hundred thousand rows at most), so file artifacts are simpler and reproducible. We would add a database if data grew or became live.

**19. How do you prevent four people from breaking each other's work?**
Contract-first design (`ARCHITECTURE_AND_API.md`), stub artifacts and mock JSON, folder ownership, small PRs, Postman and integration tests.

**20. How would this work on live data?**
Replace the CSV loader with a feed, run the same feature code on the latest interval, keep the bands fixed from the calibration period (re-calibrate on a schedule), and add a weather-forecast API for next-day expected generation.

**21. What are the limitations?**
34 days and two plants, one plant-level sensor, no rainfall/cloud/maintenance/curtailment data, tariff assumption, capacity proxy instead of rated capacity. We list them in the Handbook and in the app.

**22. What is new compared to a standard Kaggle notebook on this dataset?**
A deployed application with seven features; a fleet-normal model plus peer comparison; calibrated bands; an evidence ladder with confidence and "what would confirm"; a synthetic-injection benchmark on unseen days; tiered financial estimates; and a strict no-fault-without-evidence policy.

## Quick facts to memorise

- 2 plants, 22 inverters each, 15-minute data, about 34 days.
- Target: inverter AC power (kW). Features: weather and time only.
- Split: first ~70% of days train, next 15% validation, last 15% test.
- Primary metrics: daylight MAE, RMSE, R2, WAPE.
- Event rule: outside the 99% band for at least 3 consecutive intervals.
- Categories: data_quality, weather_transient, fleet_wide, inverter_specific, unexplained.
