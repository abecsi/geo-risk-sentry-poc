import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from geopy.geocoders import Nominatim
from duckduckgo_search import DDGS

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Geo-Risk Sentry", page_icon="🌍", layout="wide")

# --- 2. ILLUSTRATIVE ASSET LIST (TIER 1) ---
# Hand-entered, approximate coordinates from public sources (not independently verified).
# Normals are rough December daily averages (avg_temp in °C, avg_rain in mm/day).
ASSET_DB = {
    "TSLA": {
        "Factory": {"name": "Gigafactory Berlin", "lat": 52.3936, "lon": 13.7984, "avg_temp": 2.5, "avg_rain": 1.5},
        "Logistics": {"name": "Port of Zeebrugge", "lat": 51.3328, "lon": 3.2064, "avg_temp": 5.0, "avg_rain": 2.0}
    },
    "NHY.OL": {
        "Factory": {"name": "Sunndal Aluminum Smelter", "lat": 62.6753, "lon": 8.5627, "avg_temp": -1.2, "avg_rain": 4.5},
        "Logistics": {"name": "Port of Sunndalsøra", "lat": 62.6790, "lon": 8.5400, "avg_temp": -0.5, "avg_rain": 4.0}
    },
    "ASML": {
        "Factory": {"name": "Veldhoven Fabrication Plant", "lat": 51.4082, "lon": 5.4184, "avg_temp": 4.2, "avg_rain": 2.1},
        "Logistics": {"name": "Eindhoven Cargo Hub", "lat": 51.4584, "lon": 5.3913, "avg_temp": 4.0, "avg_rain": 2.1}
    },
    "SHELL": {
        "Factory": {"name": "Pernis Refinery (Rotterdam)", "lat": 51.8833, "lon": 4.3833, "avg_temp": 5.5, "avg_rain": 2.2},
        "Logistics": {"name": "Port of Rotterdam", "lat": 51.9500, "lon": 4.1333, "avg_temp": 5.5, "avg_rain": 2.2}
    },
    "EQNR": {
        "Factory": {"name": "Mongstad Refinery", "lat": 60.8080, "lon": 5.0380, "avg_temp": 3.5, "avg_rain": 6.5},
        "Logistics": {"name": "Kollsnes Gas Hub", "lat": 60.5500, "lon": 4.8333, "avg_temp": 4.0, "avg_rain": 6.0}
    },
    "NOVN.SW": {
        "Factory": {"name": "Stein Sterile Manufacturing Site", "lat": 47.5422, "lon": 7.9536, "avg_temp": 1.5, "avg_rain": 2.5},
        "Logistics": {"name": "Basel Supply Hub", "lat": 47.5623, "lon": 7.5756, "avg_temp": 2.0, "avg_rain": 2.3}
    },
    "NESN.SW": {
        "Factory": {"name": "Nespresso Production (Orbe)", "lat": 46.7237, "lon": 6.5362, "avg_temp": 0.8, "avg_rain": 2.8},
        "Logistics": {"name": "Distribution Center Avenches", "lat": 46.8800, "lon": 7.0400, "avg_temp": 1.0, "avg_rain": 2.5}
    }
}

# TIER 2: Static demo snapshots (approximate, not live), used only for the same ticker when Yahoo Finance is unavailable
DEMO_DATA = {
    "ASML": {"longName": "ASML Holding N.V.", "sector": "Technology", "marketCap": 380000000000, "currency": "EUR", "totalRevenue": 21000000000, "city": "Veldhoven", "country": "Netherlands"},
    "NHY.OL": {"longName": "Norsk Hydro ASA", "sector": "Basic Materials", "marketCap": 130000000000, "currency": "NOK", "totalRevenue": 150000000000, "city": "Oslo", "country": "Norway"},
    "NESN.SW": {"longName": "Nestlé S.A.", "sector": "Consumer Defensive", "marketCap": 260000000000, "currency": "CHF", "totalRevenue": 93000000000, "city": "Vevey", "country": "Switzerland"}
}

# --- 3. HELPER FUNCTIONS ---

def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1_000_000_000_000: return f"{num / 1_000_000_000_000:.2f} T"
    elif num >= 1_000_000_000: return f"{num / 1_000_000_000:.2f} B"
    elif num >= 1_000_000: return f"{num / 1_000_000:.2f} M"
    else: return f"{num:,.0f}"

def get_coordinates(city, country):
    try:
        geolocator = Nominatim(user_agent="geo_risk_app")
        location = geolocator.geocode(f"{city}, {country}")
        return (location.latitude, location.longitude) if location else (None, None)
    except Exception:
        return None, None

@st.cache_data(ttl=600)
def get_live_weather(lat, lon):
    """Returns (rain_mm, wind_kmh, temp_max_c), or None if the data is unavailable."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,windspeed_10m_max,temperature_2m_max&timezone=auto"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        daily = res.json()['daily']
        values = (daily['precipitation_sum'][0], daily['windspeed_10m_max'][0], daily['temperature_2m_max'][0])
        if any(v is None for v in values):
            return None
        return values
    except Exception:
        # Signal "unavailable" explicitly rather than returning zeros that read as "no risk"
        return None

def calculate_revenue_at_risk(info, rain, temp):
    """Illustrative heuristic only: step-function thresholds and fixed sector weights, not a calibrated or validated model."""
    revenue = info.get('totalRevenue')
    if not revenue:
        return None, None, 0.0, "Revenue unavailable"
    daily_rev = revenue / 365
    sector = info.get('sector', 'Unknown')
    vulnerability = 1.0 if any(x in sector for x in ['Energy', 'Materials', 'Utilities']) else 0.4

    rain_drag = 0.5 if rain > 50 else (0.15 if rain > 20 else 0.0)
    heat_drag = 0.25 if temp > 40 else (0.08 if temp > 32 else 0.0) # Assumed thermal stress on efficiency

    disruption = max(rain_drag, heat_drag)
    driver = "Heat Stress" if heat_drag > rain_drag else "Precipitation"
    if disruption == 0: driver = "None"

    return daily_rev, daily_rev * vulnerability * disruption, disruption, driver

def get_real_esg(stock_obj):
    try:
        sus = stock_obj.sustainability
        if sus is not None and not sus.empty:
            score = sus.loc['totalEsg', 'esgScores']
            label = "Low" if score < 20 else ("Medium" if score < 30 else "High")
            return score, label
    except Exception:
        pass
    return None, None

def get_news(company):
    """Returns a list of articles, or None if the search failed."""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(f"{company} climate risk supply chain", max_results=3):
                results.append(r)
    except Exception:
        return None
    return results

# --- 4. UI COMPONENTS ---

st.title("🌍 Geo-Risk Sentry")
st.markdown("### Educational proof of concept: physical weather risk at asset locations")

with st.sidebar:
    st.header("Asset Selection")
    ticker = st.text_input("Enter Stock Ticker:", "NHY.OL").upper()
    st.caption("Site-level examples: TSLA, NHY.OL, ASML, SHELL, EQNR, NOVN.SW, NESN.SW")
    st.divider()
    asset_type = st.selectbox("Asset Layer:", ["Headquarters", "Primary Factory", "Logistics Hub"])

if ticker:
    # --- A. DATA ACQUISITION ---
    # Try Yahoo Finance first; fall back to a static snapshot only for the same ticker.
    # Unknown tickers stop with an error instead of silently showing another company.
    info, stock, is_demo_mode = None, None, False
    try:
        stock = yf.Ticker(ticker)
        if 'longName' in stock.info:
            info = stock.info
    except Exception:
        stock = None

    if info is None:
        if ticker in DEMO_DATA:
            info = DEMO_DATA[ticker]
            stock = None
            is_demo_mode = True
            st.warning(f"⚠️ Live data unavailable for '{ticker}'. Showing a static demo snapshot (approximate, not live).")
        else:
            st.error(f"❌ Ticker '{ticker}' not found or market data unavailable. No data shown.")
            st.stop()

    # --- B. GEOLOCATION LOGIC ---
    # 1. Default: Geocode the City/Country from the info dictionary
    city = info.get('city', 'Unknown')
    country = info.get('country', 'Unknown')
    lat, lon = get_coordinates(city, country)

    loc_name = f"{city} (HQ)"
    b_temp = None
    b_rain = None
    exact = False

    # 2. Tier 1 Override: use site coordinates from ASSET_DB if available
    if ticker in ASSET_DB:
        db_key = "Factory" if "Factory" in asset_type else ("Logistics" if "Logistics" in asset_type else None)

        if db_key:
            asset_data = ASSET_DB[ticker][db_key]
            lat = asset_data['lat']
            lon = asset_data['lon']
            loc_name = asset_data['name']
            b_temp = asset_data.get('avg_temp')
            b_rain = asset_data.get('avg_rain')
            exact = True

    # 3. No location found: stop rather than assess risk at an arbitrary default location
    if lat is None:
        st.error(f"❌ Could not locate '{city}, {country}'. Location-based risk cannot be assessed.")
        st.stop()

    # --- C. WEATHER & HEURISTIC ---
    weather = get_live_weather(lat, lon)
    weather_ok = weather is not None
    daily_rev = None
    if weather_ok:
        rain, wind, temp = weather
        daily_rev, est_loss, drag_pct, driver = calculate_revenue_at_risk(info, rain, temp)
    else:
        st.warning("⚠️ Weather data unavailable (Open-Meteo request failed). Risk metrics are not shown.")

    # --- ESG: shown only when the data source returns a value; never estimated ---
    esg_score, esg_label = None, None
    if not is_demo_mode and stock:
        esg_score, esg_label = get_real_esg(stock)

    # --- 5. DASHBOARD LAYOUT ---

    # ROW 1: METRICS
    st.subheader(f"📊 Company Overview: {info.get('longName')}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sector", info.get('sector', 'Unknown'))
    m2.metric("Market Cap", f"{format_large_number(info.get('marketCap'))} {info.get('currency', 'USD')}")
    m3.metric("Asset Location", loc_name.split('(')[0])
    if esg_score is not None:
        m4.metric("ESG Risk Score (Yahoo)", f"{esg_score:.1f}", delta=esg_label, delta_color="inverse")
    else:
        m4.metric("ESG Risk Score (Yahoo)", "N/A", help="No ESG score returned by the data source.")

    # ROW 2: ANOMALY VS. APPROXIMATE NORMS (if in DB)
    if b_temp is not None and weather_ok:
        st.divider()
        st.subheader("📉 Weather vs. Approximate Norms")
        c1, c2, c3 = st.columns(3)
        c1.metric("Temperature Anomaly (approx.)", f"{temp - b_temp:+.1f} °C", help=f"Today's max vs. rough December daily norm ({b_temp}°C)", delta_color="inverse")
        rain_diff = rain - b_rain  # both in mm/day
        c2.metric("Precipitation vs. Norm (approx.)", "Drier" if rain_diff < 0 else "Wetter", f"{rain_diff:+.1f} mm/day", delta_color="off")
        c3.info("**Baseline:** Hand-entered December daily averages. Indicative only, and not seasonally adjusted outside December.")

    # ROW 3: MAP
    st.divider()
    st.subheader(f"📍 Asset Monitor: {loc_name}")
    if exact: st.caption(f"Approximate site coordinates (public sources): {loc_name}")
    st.map(pd.DataFrame({'lat': [lat], 'lon': [lon], 'size': [150]}), zoom=11, size='size')

    # ROW 4: FINANCIALS
    st.divider()
    st.subheader("💰 Illustrative Revenue-at-Risk Heuristic")
    st.caption("Not Value-at-Risk. Simple threshold rules and fixed sector weights; uncalibrated and unvalidated.")
    if weather_ok and daily_rev is not None:
        f1, f2, f3 = st.columns(3)
        f1.metric("Est. Daily Revenue", f"{format_large_number(daily_rev)} {info.get('currency', 'USD')}")
        f2.metric("Assumed Operational Drag", f"{drag_pct*100:.1f}%", delta=f"{temp}°C / {rain}mm", delta_color="inverse" if drag_pct > 0 else "off")
        f3.metric("Illustrative Revenue at Risk", f"{format_large_number(est_loss)} {info.get('currency', 'USD')}", delta=f"Driver: {driver}", delta_color="inverse")
    else:
        st.info("Not available: requires both weather data and reported revenue.")

    # ROW 5: SUMMARY & NEWS
    st.divider()
    col_l, col_r = st.columns([2,1])
    with col_l:
        st.subheader("📝 Rule-Based Summary")
        if weather_ok and daily_rev is not None:
            risk_lvl = "HIGH" if drag_pct > 0.1 else ("MODERATE" if drag_pct > 0 else "LOW")
            colour = {"HIGH": "red", "MODERATE": "orange", "LOW": "green"}[risk_lvl]
            st.markdown(f"**Status:** :{colour}[{risk_lvl}] (heuristic thresholds)")
            if drag_pct > 0:
                st.write(f"Current conditions at {loc_name} exceed the {driver.lower()} threshold. Impact uses a fixed weight for the {info.get('sector')} sector.")
            else:
                st.write(f"Current conditions at {loc_name} are below all heuristic thresholds.")

            memo = (f"GEO-RISK NOTE (educational PoC, heuristic only)\n"
                    f"Target: {info.get('longName')}\nLocation: {loc_name}\n"
                    f"Data: {'static demo snapshot' if is_demo_mode else 'live Yahoo Finance'}\n"
                    f"Heuristic level: {risk_lvl}\nIllustrative revenue at risk: {format_large_number(est_loss)}")
            st.download_button("📄 Download Summary Note", memo, f"Risk_Note_{ticker}.txt", "text/plain")
        else:
            st.markdown("**Status:** :gray[DATA UNAVAILABLE]")

    with col_r:
        st.subheader("📰 Recent News (DuckDuckGo)")
        news = get_news(info.get('longName'))
        if news is None:
            st.warning("News search unavailable.")
        elif not news:
            st.caption("No recent articles found.")
        for n in news or []:
            with st.expander(n.get('title', 'News')):
                st.write(n.get('body', 'No snippet available.'))
                st.markdown(f"[Read More]({n.get('url')})")

st.divider()
st.warning("⚖️ **Educational PoC:** Built by Attila Bécsi. Open APIs only; heuristic, unvalidated outputs. Not financial advice. See README for limitations.")
