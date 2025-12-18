import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import datetime
from geopy.geocoders import Nominatim
from duckduckgo_search import DDGS

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Geo-Risk Sentry", page_icon="🌍", layout="wide")

# --- 2. PROPRIETARY ASSET DATABASE (TIER 1) ---
# Includes coordinates and "Climate Normals" for Context-Aware Anomaly Detection
# Normals represent approximate historical averages for December
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
    },
    "OCP": { # For Morocco Field Research Content
        "Factory": {"name": "Jorf Lasfar Complex", "lat": 33.125, "lon": -8.636, "avg_temp": 16.5, "avg_rain": 1.2},
        "Logistics": {"name": "Phosphate Export Terminal", "lat": 33.130, "lon": -8.640, "avg_temp": 16.5, "avg_rain": 1.0}
    }
}

# TIER 2: Snapshot Fallbacks (If API is throttled)
DEMO_DATA = {
    "ASML": {"longName": "ASML Holding N.V.", "sector": "Technology", "marketCap": 380000000000, "currency": "EUR", "totalRevenue": 21000000000, "city": "Veldhoven", "country": "Netherlands"},
    "NHY.OL": {"longName": "Norsk Hydro ASA", "sector": "Basic Materials", "marketCap": 130000000000, "currency": "NOK", "totalRevenue": 150000000000, "city": "Oslo", "country": "Norway"},
    "NESN.SW": {"longName": "Nestlé S.A.", "sector": "Consumer Defensive", "marketCap": 260000000000, "currency": "CHF", "totalRevenue": 93000000000, "city": "Vevey", "country": "Switzerland"},
    "OCP": {"longName": "OCP Group", "sector": "Basic Materials", "marketCap": 15000000000, "currency": "MAD", "totalRevenue": 9000000000, "city": "Casablanca", "country": "Morocco"}
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
    except: return None, None

@st.cache_data(ttl=600)
def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,windspeed_10m_max,temperature_2m_max&timezone=auto"
        res = requests.get(url).json()
        return res['daily']['precipitation_sum'][0], res['daily']['windspeed_10m_max'][0], res['daily']['temperature_2m_max'][0]
    except: return 0, 0, 0

def calculate_va_r(info, rain, temp):
    revenue = info.get('totalRevenue', 5_000_000_000)
    daily_rev = revenue / 365
    sector = info.get('sector', 'Unknown')
    vulnerability = 1.0 if any(x in sector for x in ['Energy', 'Materials', 'Utilities']) else 0.4
    
    rain_drag = 0.5 if rain > 50 else (0.15 if rain > 20 else 0.0)
    heat_drag = 0.25 if temp > 40 else (0.08 if temp > 32 else 0.0) # Thermal stress on efficiency
    
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
    except: pass
    return None, None

def get_news(company):
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(f"{company} climate risk supply chain", max_results=3):
                results.append(r)
    except: pass
    return results

# --- 4. UI COMPONENTS ---

st.title("🌍 Geo-Risk Sentry: AI-Driven Asset Analysis")
st.markdown("### Context-Aware Physical Risk & ESG Intelligence")

with st.sidebar:
    st.header("Asset Selection")
    ticker = st.text_input("Enter Stock Ticker:", "NHY.OL").upper()
    st.caption("✨ Deep Data: TSLA, NHY.OL, ASML, SHELL, EQNR, NESN.SW, OCP")
    st.divider()
    asset_type = st.selectbox("Asset Layer:", ["Headquarters", "Primary Factory", "Logistics Hub"])

if ticker:
    # --- A. DATA ACQUISITION (Robust Fallback Logic) ---
    # 1. Check Internal Demo Data First (Fastest, supports OCP)
    if ticker in DEMO_DATA:
        info = DEMO_DATA[ticker]
        stock = None
        is_demo_mode = True
    else:
        # 2. Try Yahoo Finance
        try:
            stock = yf.Ticker(ticker)
            if 'longName' in stock.info:
                info = stock.info
                is_demo_mode = False
            else:
                # Yahoo failed to find ticker -> Fallback to ASML
                info = DEMO_DATA["ASML"]
                is_demo_mode = True
        except:
            # Internet/API Error -> Fallback to ASML
            info = DEMO_DATA["ASML"]
            is_demo_mode = True
    
    if is_demo_mode and ticker not in DEMO_DATA:
        st.warning(f"⚠️ Could not fetch live data for '{ticker}'. Showing demo data for ASML as placeholder.")

    # --- B. GEOLOCATION LOGIC ---
    # 1. Default: Geocode the City/Country from the info dictionary
    city = info.get('city', 'Unknown')
    country = info.get('country', 'Unknown')
    
    # Try to find coordinates
    lat, lon = get_coordinates(city, country)
    
    # Initialize Context Variables (Default values to prevent NameError)
    loc_name = f"{city} (HQ)"
    b_temp = None
    b_rain = None
    exact = False

    # 2. Tier 1 Override: Check if we have specific coordinates in ASSET_DB
    if ticker in ASSET_DB:
        # Determine which asset type user selected
        db_key = "Factory" if "Factory" in asset_type else ("Logistics" if "Logistics" in asset_type else None)
        
        if db_key:
            asset_data = ASSET_DB[ticker][db_key]
            # OVERWRITE lat/lon with precise data
            lat = asset_data['lat']
            lon = asset_data['lon']
            loc_name = asset_data['name']
            b_temp = asset_data.get('avg_temp')
            b_rain = asset_data.get('avg_rain')
            exact = True

    # 3. Final Safety Net: If lat is still None (Geocoding failed + No DB entry)
    if lat is None:
        lat, lon = 59.91, 10.75 # Default to Oslo
        st.error(f"Could not locate '{city}, {country}'. Defaulting map to Oslo.")

    # --- C. LIVE RISK ENGINE ---
    # Now lat/lon are guaranteed to exist
    rain, wind, temp = get_live_weather(lat, lon)
    daily_rev, est_loss, drag_pct, driver = calculate_va_r(info, rain, temp)
    
    # --- FIXED ESG LOGIC ---
    esg_score = None
    esg_label = "N/A"

    # 1. Try Real Data (If Yahoo is working)
    if not is_demo_mode and stock:
        esg_score, esg_label = get_real_esg(stock)
    
    # 2. If Real Data failed, check Dictionary Fallbacks
    if esg_score is None:
        # Check 'info' first (safely)
        esg_score = info.get('esgScores', {}).get('totalEsg')
        
        # If still None, check DEMO_DATA explicitly
        if esg_score is None and ticker in DEMO_DATA:
             # USE .get() TO PREVENT KEYERROR CRASH
             esg_score = DEMO_DATA[ticker].get('esgScores', {}).get('totalEsg')
        
        if esg_score:
            esg_label = "Est. (Medium)"

    # --- 5. DASHBOARD LAYOUT ---
    
    # ROW 1: METRICS
    st.subheader(f"📊 Portfolio Insight: {info.get('longName')}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sector", info.get('sector', 'Unknown'))
    m2.metric("Market Cap", f"{format_large_number(info.get('marketCap'))} {info.get('currency', 'USD')}")
    m3.metric("Asset Location", loc_name.split('(')[0])
    m4.metric("Sustainalytics Risk", f"{esg_score:.1f}" if esg_score else "22.4", delta=esg_label if esg_label else "Medium", delta_color="inverse")

    # ROW 2: CONTEXT-AWARE SCAN (If in DB)
    if b_temp is not None:
        st.divider()
        st.subheader("📉 Context-Aware Anomaly Scan")
        c1, c2, c3 = st.columns(3)
        c1.metric("Temperature Anomaly", f"{temp - b_temp:+.1f} °C", help=f"Vs. Historical Norm ({b_temp}°C)", delta_color="inverse")
        rain_diff = rain - (b_rain/30)
        c2.metric("Precipitation Delta", "Drier" if rain_diff < 0 else "Wetter", f"{rain_diff:+.1f} mm", delta_color="off")
        c3.info(f"**Baseline:** Benchmarking against historical {datetime.datetime.now().strftime('%B')} averages for these coordinates.")

    # ROW 3: MAP
    st.divider()
    st.subheader(f"📍 Asset Monitor: {loc_name}")
    if exact: st.success(f"✅ Verified Asset Coordinates: {loc_name}")
    st.map(pd.DataFrame({'lat': [lat], 'lon': [lon], 'size': [150]}), zoom=11, size='size')

    # ROW 4: FINANCIALS
    st.divider()
    st.subheader("💰 Parametric Revenue-at-Risk (VaR)")
    f1, f2, f3 = st.columns(3)
    f1.metric("Est. Daily Revenue", f"{format_large_number(daily_rev)} {info.get('currency', 'USD')}")
    f2.metric("Operational Drag", f"{drag_pct*100:.1f}%", delta=f"{temp}°C / {rain}mm", delta_color="inverse" if drag_pct > 0 else "off")
    f3.metric("Capital at Risk", f"{format_large_number(est_loss)} {info.get('currency', 'USD')}", delta=f"Driver: {driver}", delta_color="inverse")

    # ROW 5: AI & NEWS
    st.divider()
    col_l, col_r = st.columns([2,1])
    with col_l:
        st.subheader("🤖 AI Strategic Insight")
        risk_lvl = "HIGH" if drag_pct > 0.1 else ("MODERATE" if drag_pct > 0 else "LOW")
        st.markdown(f"**Status:** :{ 'red' if risk_lvl=='HIGH' else 'orange'}[{risk_lvl} RISK] detected.")
        st.write(f"Current conditions at {loc_name} reflect {driver.lower()} thresholds being exceeded. Financial impact is calculated based on {info.get('sector')} vulnerability curves.")
        
        # Download Button
        memo = f"GEO-RISK MEMO\nTarget: {info.get('longName')}\nLocation: {loc_name}\nRisk: {risk_lvl}\nVaR: {format_large_number(est_loss)}"
        st.download_button("📄 Download Audit Memo", memo, f"Risk_Memo_{ticker}.txt", "text/plain")

    with col_r:
        st.subheader("📰 Live OSINT News")
        for n in get_news(info.get('longName')):
            with st.expander(n.get('title', 'News')):
                st.write(n.get('body', 'No snippet available.'))
                st.markdown(f"[Read More]({n.get('url')})")

st.divider()
st.warning("⚖️ **Educational PoC:** Built by Attila Bécsi. All data from open APIs. Not financial advice.")
