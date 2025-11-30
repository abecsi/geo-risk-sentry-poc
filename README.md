# 🌍 Geo-Risk Sentry (Proof of Concept)

### 🚀 Overview
This project is a functional prototype demonstrating how **AI Agents** and **Real-Time Geospatial Data** can automate ESG risk assessments for Asset Managers.

Unlike traditional static ESG reports, this tool performs live OSINT (Open Source Intelligence) lookups to determine physical climate exposure.

### ⚙️ How it Works
1.  **Dynamic Geocoding:** Converts any corporate ticker (e.g., `NHY.OL`, `MSFT`) into Headquarters coordinates using the **Nominatim API**.
2.  **Live Climate Data:** Connects to **Open-Meteo** to fetch real-time precipitation and wind speed data for that specific asset location.
3.  **Risk Logic:** A proprietary Python algorithm calculates a dynamic Risk Score based on live weather severity.
4.  **Financial Context:** Ingests live market data (Market Cap, Sector, Beta) via **Yahoo Finance**.

### 🛠️ Tech Stack
*   **Core:** Python 3.11
*   **Frontend:** Streamlit
*   **Data Engineering:** Pandas, NumPy
*   **APIs:** Open-Meteo (Weather), Yahoo Finance (Market), Nominatim (Geo)

### 🔮 Future Roadmap (Orbitalytics Vision)
*   Integration with **Sentinel-2 Satellite Imagery** for flood visualization.
*   Expansion to multi-asset supply chain mapping.
*   LLM integration for automated report generation.

---
*Created by Attila Bécsi - (https://www.linkedin.com/in/attila-becsi/)
