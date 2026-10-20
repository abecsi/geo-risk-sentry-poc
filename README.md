# 🌍 Geo-Risk Sentry (Educational Proof of Concept)

[![tests](https://github.com/abecsi/geo-risk-sentry-poc/actions/workflows/tests.yml/badge.svg)](https://github.com/abecsi/geo-risk-sentry-poc/actions/workflows/tests.yml)

**Live demo:** https://geo-risk-sentry-attila-becsi.streamlit.app/

## What it is
A small Streamlit prototype that looks at today's weather at a company's site and turns it into a simple, illustrative revenue-impact figure. It uses **open APIs only**:

| Layer | Source |
|---|---|
| Company financials, ESG score (when returned) | Yahoo Finance (`yfinance`) |
| Weather (daily rain, wind, max temperature) | Open-Meteo |
| HQ geocoding | Open-Meteo geocoding |
| News headlines | DuckDuckGo search |

A short hand-entered list of approximate site coordinates (e.g. Tesla Gigafactory Berlin, Norsk Hydro Sunndal) lets you switch between HQ, factory and logistics locations for a few example tickers.

## How it works
1. Enter a ticker (e.g. `NHY.OL`, `EQNR`, `TSLA`).
2. Financial data is fetched from Yahoo Finance. If that fails, a static snapshot is used for a few tickers and flagged as such. Unknown tickers show an error; no substitute company is shown.
3. The site location comes from the example list or from geocoding the HQ city.
4. Today's weather is fetched from Open-Meteo. If it is unavailable, the app says so and shows no risk figures.
5. A **heuristic** applies step thresholds (rain > 20/50 mm, max temp > 32/40 °C) and a fixed sector weight to daily revenue, giving an *illustrative revenue-at-risk* figure and a rule-based LOW/MODERATE/HIGH label.

## Features
- **Stress scenario:** sidebar sliders add a rain or heat shock to today's forecast and show the change against the baseline.
- **7-day outlook:** the illustrative revenue at risk for each day of the Open-Meteo forecast.
- **Data lineage & quality panel:** the source and status (live, static, approximate or unavailable) of every data element, with a retrieval timestamp.
- **Model card:** the purpose, method, assumptions, limitations and controls of the heuristic, shown in the app.
- **Tested calculation logic:** the heuristic lives in [`risk_model.py`](risk_model.py), separate from the UI. Unit tests in [`tests/`](tests/) run on every push through GitHub Actions.

## Known limitations
- **Not Value-at-Risk.** The impact curve is a hand-set step function with no statistical basis, calibration or backtesting.
- **No validation.** Thresholds and sector weights are assumptions and have not been tested against real outages.
- **Demo fallback data.** Static snapshots are approximate and dated. Site coordinates and climate normals are hand-entered approximations of December daily averages.
- **Single-day view.** It uses one daily forecast value and ignores duration, asset design, insurance and business continuity.
- **No ESG estimation.** If no ESG score is returned, the app shows N/A.
- **Limited testing.** Unit tests cover only the calculation logic. There are no integration tests, structured logging or full input schema validation.

## What a production version in a bank would need
If a tool like this were used for decisions, it would be an End User Computing (EUC) tool, or possibly a model, and would need to be governed as one:

- **Ownership and inventory:** a named owner, EUC/model inventory registration and a criticality rating.
- **Testing:** unit tests for the calculation logic, regression tests and CI gating.
- **Data quality controls:** source checks (completeness, staleness, range checks), reconciliation and documented lineage (BCBS 239 principles).
- **Input validation and error handling:** explicit failure states and no silent defaults (partly done in this PoC).
- **Logging and audit trail:** versioned inputs and outputs, so results can be reproduced.
- **Model documentation:** purpose, methodology, assumptions, limitations and intended use.
- **Independent review:** validation by a second line (model risk), with calibration and backtesting of the impact function, and ongoing performance monitoring.
- **Change management and access control:** peer-reviewed changes, segregation of duties and controlled deployment.

## Tech stack
Python 3.11 · Streamlit · Pandas · yfinance · Open-Meteo · DuckDuckGo search

---
**Disclaimer:** Personal educational project built on public APIs. Not investment advice.

*Created by Attila Bécsi ([LinkedIn](https://www.linkedin.com/in/attila-becsi/))*
