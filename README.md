# 🌍 Geo-Risk Sentry (Proof of Concept)

### 🚀 Overview
**Geo-Risk Sentry** is a live physical climate risk dashboard designed for the next generation of Asset Management. 

Unlike static ESG reports that rely on backward-looking data, this tool uses **AI Agents** and **Real-Time OSINT (Open Source Intelligence)** to assess how live weather events impact specific corporate balance sheets.

**Live Demo:** (https://geo-risk-sentry-attila-becsi.streamlit.app/)

### 🧠 Core Capabilities
The application integrates three distinct data layers to simulate a "Digital Twin" of physical risk:

1.  **Multi-Asset Resolution:**
    *   Distinguishes between **Corporate HQs**, **Manufacturing Plants**, and **Logistics Hubs**.
    *   Utilizes a **Tiered Data Architecture**:
        *   *Tier 1:* Validated proprietary coordinates for major assets (e.g., Tesla Gigafactory Berlin, Norsk Hydro Sunndal).
        *   *Tier 2:* Dynamic geocoding fallback for the "Long Tail" of global assets.

2.  **Parametric Revenue-at-Risk (VaR) Model:**
    *   Translates weather severity (mm of rain, wind speed) into **Financial Impact**.
    *   Calculates `Daily Revenue-at-Risk` based on **Sector Vulnerability Factors** (e.g., Energy/Manufacturing assets are weighted higher for physical disruption than Tech/Services).

3.  **AI-Driven OSINT (News Intelligence):**
    *   Scrapes **Global News** (via DuckDuckGo API) to detect real-time sentiment regarding supply chain disruptions or climate events.
    *   Includes **Entity Disambiguation** logic to filter out irrelevant noise (e.g., distinguishing "Alphabet Inc." from dictionary definitions, or "Tesla" the car company from "Tesla" the GPU architecture).
    *   Enforces **Context-Aware Filtering** to prioritize business and risk-related headlines over general consumer news.

### ⚙️ Technical Logic
1.  **Input:** User enters a financial ticker (e.g., `NHY.OL`, `NESN.SW`, `TSLA`).
2.  **Data Ingestion:** Fetches live financial data (Market Cap, Revenue, Beta) via **Yahoo Finance**.
3.  **Geospatial Processing:** Determines the precise coordinates of the asset using the proprietary Asset DB or **Nominatim** geocoding.
4.  **Risk Trigger:** Queries **Open-Meteo API** for real-time precipitation and wind speed at those coordinates.
5.  **Output:** Generates a live "Risk Scorecard" and an AI-generated strategic insight summary.

### 🛠️ Tech Stack
*   **Core:** Python 3.11
*   **Frontend:** Streamlit
*   **Data Engineering:** Pandas, NumPy
*   **Geospatial:** Geopy, Nominatim API
*   **Intelligence:** DuckDuckGo Search (OSINT), Open-Meteo (Weather), Yahoo Finance (Financials)

### 🔮 Future Roadmap (Orbitalytics Vision)
*   **Satellite Integration:** Direct ingestion of Sentinel-2 imagery to visualize flood water levels overlaying factory perimeters.
*   **Supply Chain Graph:** Automatic mapping of Tier 1 and Tier 2 suppliers.
*   **LLM Report Generation:** Automated PDF generation for Investment Committee memos using a new LLM.

---
**Disclaimer:** This is a personal project demonstrating technical product management and quantitative risk capabilities. It uses public APIs and is not intended for commercial investment advice.

*Created by Attila Bécsi - (https://www.linkedin.com/in/attila-becsi/)*
