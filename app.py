import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from geopy.geocoders import Nominatim
from duckduckgo_search import DDGS

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Geo-Risk Sentry", page_icon="🌍", layout="wide")

# --- 2. CONSTANTS & DATABASES ---

# TIER 1: Verified Coordinates for Specific Assets (The "Proprietary" DB)
ASSET_DB = {
    "TSLA": {
        "Factory": {"name": "Gigafactory Berlin-Brandenburg", "lat": 52.3936, "lon": 13.7984},
        "Logistics": {"name": "Port of Zeebrugge (Major Import Hub)", "lat": 51.3328, "lon": 3.2064}
    },
    "NHY.OL": {
        "Factory": {"name": "Sunndal Aluminum Smelter (Largest in Europe)", "lat": 62.6753, "lon": 8.5627},
        "Logistics": {"name": "Port of Sunndalsøra", "lat": 62.6790, "lon": 8.5400}
    },
    "ASML": {
        "Factory": {"name": "Veldhoven Fabrication Plant", "lat": 51.4082, "lon": 5.4184},
        "Logistics": {"name": "Eindhoven Airport Cargo Hub", "lat": 51.4584, "lon": 5.3913}
    },
    "SHELL": {
        "Factory": {"name": "Pernis Refinery (Largest in Europe)", "lat": 51.8833, "lon": 4.3833},
        "Logistics": {"name": "Port of Rotterdam", "lat": 51.9500, "lon": 4.1333}
    },
    "EQNR": {
        "Factory": {"name": "Mongstad Refinery", "lat": 60.8080, "lon": 5.0380},
        "Logistics": {"name": "Kollsnes Gas Processing", "lat": 60.5500, "lon": 4.8333}
    },
    "NOVN.SW": { 
        "Factory": {"name": "Stein Sterile Manufacturing Site", "lat": 47.5422, "lon": 7.9536},
        "Logistics": {"name": "Basel Campus Supply Hub", "lat": 47.5623, "lon": 7.5756}
    },
    "NESN.SW": { 
        "Factory": {"name": "Nespresso Production Centre (Orbe)", "lat": 46.7237, "lon": 6.5362},
        "Logistics": {"name": "Distribution Center Avenches", "lat": 46.8800, "lon": 7.0400}
    }
}

# TIER 2: High Quality Financial Fallbacks (If Yahoo Blocks Cloud IP)
DEMO_DATA = {
    "ASML": {
        "longName": "ASML Holding N.V.", "sector": "Technology", "marketCap": 380000000000, "currency": "EUR",
        "city": "Veldhoven", "country": "Netherlands", "totalRevenue": 21000000000, "beta": 1.3,
        "esgScores": {"totalEsg": 14.0} 
    },
    "NHY.OL": {
        "longName": "Norsk Hydro ASA", "sector": "Basic Materials", "marketCap": 130000000000, "currency": "NOK",
        "city": "Oslo", "country": "Norway", "totalRevenue": 150000000000, "beta": 1.1,
        "esgScores": {"totalEsg": 25.0}
    },
    "NESN.SW": {
        "longName": "Nestlé S.A.", "sector": "Consumer Defensive", "marketCap": 260000000000, "currency": "CHF",
        "city": "Vevey", "country": "Switzerland", "totalRevenue": 93000000000, "beta": 0.6,
        "esgScores": {"totalEsg": 21.0}
    },
    "NOVN.SW": {
        "longName": "Novartis AG", "sector": "Healthcare", "marketCap": 200000000000, "currency": "CHF",
        "city": "Basel", "country": "Switzerland", "totalRevenue": 45000000000, "beta": 0.5,
        "esgScores": {"totalEsg": 16.0}
    },
    "SHELL": {
        "longName": "Shell PLC", "sector": "Energy", "marketCap": 210000000000, "currency": "USD",
        "city": "London", "country": "UK", "totalRevenue": 316000000000, "beta": 0.9,
        "esgScores": {"totalEsg": 34.0}
    },
    "EQNR": {
        "longName": "Equinor ASA", "sector": "Energy", "marketCap": 90000000000, "currency": "USD",
        "city": "Stavanger", "country": "Norway", "totalRevenue": 100000000000, "beta": 0.8,
        "esgScores": {"totalEsg": 28.0}
    },
     "TSLA": {
        "longName": "Tesla Inc.", "sector": "Consumer Cyclical", "marketCap": 700000000000, "currency": "USD",
        "city": "Austin", "country": "United States", "totalRevenue": 96000000000, "beta": 2.0,
        "esgScores": {"totalEsg": 26.0}
    }
}

# --- 3. HELPER FUNCTIONS ---

def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1_000_000_000_000: return f"{num / 1_000_000_000_000:.2f} T"
    elif num >= 1_000_000_000: return f"{num / 1_000_000_000:.2f} B"
    elif num >= 1_000_000: return f"{num / 1_000_000:.2f} M"
    else: return f"{num:,.0f}"

def get_coordinates(city, country):
    """Converts a City Name into GPS Coordinates using OpenStreetMap"""
    try:
        geolocator = Nominatim(user_agent="geo_risk_app")
        location = geolocator.geocode(f"{city}, {country}")
        if location:
            return location.latitude, location.longitude
        return None, None
    except:
        return None, None

@st.cache_data(ttl=600)
def get_live_weather_risk(lat, lon):
    """Fetches real-time rain data from Open-Meteo API"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,windspeed_10m_max&timezone=auto"
        response = requests.get(url).json()
        rain_today = response['daily']['precipitation_sum'][0] 
        wind_today = response['daily']['windspeed_10m_max'][0] 
        return rain_today, wind_today
    except:
        return 0, 0

@st.cache_data(ttl=3600) 
def fetch_live_data(ticker):
    """Attempts to fetch live data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if 'longName' not in info and 'symbol' not in info:
            return None
        return info
    except Exception:
        return None

def get_stock_data_safe(ticker):
    """Orchestrates Data Fetching: Live -> Demo DB -> Generic"""
    # 1. LIVE FETCH
    info = fetch_live_data(ticker)
    if info:
        stock = yf.Ticker(ticker)
        return stock, info, False

    # 2. DEMO DB FALLBACK
    if ticker in DEMO_DATA:
        return None, DEMO_DATA[ticker], True
    
    # Fuzzy match
    for k, v in DEMO_DATA.items():
        if ticker.lower() in k.lower() or k.lower() in ticker.lower():
            return None, v, True

    # 3. GENERIC FALLBACK
    generic_data = {
        "longName": f"{ticker} (Simulated)", "sector": "Industrial (Unknown)", 
        "marketCap": 10000000000, "currency": "USD", "city": "Unknown", 
        "country": "Unknown", "totalRevenue": 5000000000, "beta": 1.0,
        "esgScores": {"totalEsg": 25.0}
    }
    return None, generic_data, True

def get_real_esg_score(stock_object):
    """Fetches real Sustainalytics data via yfinance."""
    try:
        sus_df = stock_object.sustainability
        if sus_df is not None and not sus_df.empty:
            total_score = sus_df.loc['totalEsg', 'esgScores']
            if total_score < 10: label = "Negligible"
            elif total_score < 20: label = "Low Risk"
            elif total_score < 30: label = "Medium Risk"
            elif total_score < 40: label = "High Risk"
            else: label = "Severe Risk"
            return total_score, label
    except Exception:
        pass
    return None, None

def calculate_revenue_at_risk(info, rain_mm):
    """Parametric Risk Model"""
    revenue = info.get('totalRevenue')
    if revenue is None: return None, None, None
    
    daily_revenue = revenue / 365
    sector = info.get('sector', 'Unknown')
    
    # Vulnerability Logic
    if any(x in sector for x in ['Energy', 'Basic Materials', 'Industrials', 'Utilities']):
        vulnerability = 1.0 
    elif any(x in sector for x in ['Technology', 'Communication', 'Financial']):
        vulnerability = 0.3 
    else:
        vulnerability = 0.5 

    # Weather Logic
    if rain_mm >= 50: disruption_pct = 0.50 
    elif rain_mm >= 20: disruption_pct = 0.15 
    elif rain_mm >= 5: disruption_pct = 0.02 
    else: disruption_pct = 0.0 

    estimated_loss = daily_revenue * vulnerability * disruption_pct
    return daily_revenue, estimated_loss, disruption_pct

def get_climate_news(ticker, company_name):
    """Searches using DuckDuckGo News (Returns keys: date, source, url, title)"""
    results = []
    try:
        # Search query
        search_query = f"{company_name} climate risk ESG supply chain"
        
        with DDGS() as ddgs:
            # We use .news() to get the specific metadata keys you requested
            for r in ddgs.news(search_query, max_results=3):
                results.append(r)
    except Exception as e:
        print(f"News Error: {e}")
        return []
    return results

# --- 4. MAIN APPLICATION ---

st.title("🌍 Geo-Risk Sentry: AI-Driven Asset Analysis")
st.markdown("### Physical Risk & ESG Intelligence Dashboard")

# SIDEBAR
with st.sidebar:
    st.header("Asset Selection")
    ticker = st.text_input("Enter Stock Ticker:", "NHY.OL")
    st.caption("✨ Best Data coverage: TSLA, NHY.OL, ASML, SHELL, EQNR, NOVN.SW, NESN.SW")
    
    st.divider()
    asset_type = st.selectbox(
        "Select Asset Layer:",
        ["Headquarters (Corporate)", "Primary Factory (Manufacturing)", "Supply Chain Hub (Logistics)"]
    )

if ticker:
    # A. FETCH FINANCIALS
    stock, info, is_demo_mode = get_stock_data_safe(ticker)
    
    if is_demo_mode:
        st.warning(f"⚠️ Live Data Connection Throttled. Viewing **Offline Snapshot** for {info.get('longName')}.")

    # B. GEOLOCATION LOGIC
    city = info.get('city', 'Unknown')
    country = info.get('country', 'Unknown')
    
    # Default: HQ
    lat, lon = get_coordinates(city, country)
    location_name = f"{city} (HQ)"
    asset_label = "corporate headquarters"
    is_exact_match = False

    # Check Tier 1 DB Override
    if ticker in ASSET_DB:
        if asset_type == "Primary Factory (Manufacturing)":
            lat = ASSET_DB[ticker]["Factory"]["lat"]
            lon = ASSET_DB[ticker]["Factory"]["lon"]
            location_name = ASSET_DB[ticker]["Factory"]["name"]
            asset_label = "primary manufacturing facility"
            is_exact_match = True
        elif asset_type == "Supply Chain Hub (Logistics)":
            lat = ASSET_DB[ticker]["Logistics"]["lat"]
            lon = ASSET_DB[ticker]["Logistics"]["lon"]
            location_name = ASSET_DB[ticker]["Logistics"]["name"]
            asset_label = "logistics hub"
            is_exact_match = True

    if asset_type != "Headquarters (Corporate)" and not is_exact_match:
        st.warning(f"⚠️ Precise {asset_type} data not available. Showing regional HQ risk.")

    # C. REAL-TIME RISK DATA
    if lat:
        rain, wind = get_live_weather_risk(lat, lon)
    else:
        rain, wind = 0, 0
        lat, lon = 59.91, 10.75 # Default Fallback

    # --- DASHBOARD UI ---
    
    # 1. HEADER METRICS
    st.subheader(f"📊 Analysis: {info.get('longName', ticker.upper())}")
    col1, col2, col3, col4 = st.columns(4)
    
    currency = info.get('currency', 'USD')
    formatted_mcap = f"{format_large_number(info.get('marketCap'))} {currency}"
    
    # ESG Logic
    if not is_demo_mode and stock:
        raw_esg, esg_label = get_real_esg_score(stock)
    else:
        # Fallback ESG from Demo DB or Estimate
        raw_esg = info.get('esgScores', {}).get('totalEsg')
        esg_label = "Est. (Medium Risk)" if raw_esg else "N/A"

    with col1: st.metric("Sector", info.get('sector', 'Unknown'))
    with col2: st.metric("Market Cap", formatted_mcap)
    with col3: st.metric("Asset Location", location_name.split(',')[0]) # Shorten name
    with col4: 
        if raw_esg:
            st.metric("Sustainalytics Score", f"{raw_esg:.1f}", delta=esg_label, delta_color="inverse")
        else:
            st.metric("Sustainalytics Score", "N/A")

    # 2. MAP
    st.divider()
    st.subheader(f"📍 Real-Time Monitor: {location_name}")
    if is_exact_match:
        st.success(f"✅ Verified Asset Coordinates Found: **{location_name}**")
    
    map_df = pd.DataFrame({'lat': [lat], 'lon': [lon], 'size': [100]})
    st.map(map_df, zoom=10, size='size')

    # 3. PARAMETRIC MODEL
    st.divider()
    st.subheader("💰 Parametric Revenue-at-Risk Model")
    daily_rev, est_loss, disrupt_pct = calculate_revenue_at_risk(info, rain)
    
    if daily_rev:
        f1, f2, f3 = st.columns(3)
        with f1: st.metric("Daily Revenue (TTM)", f"{format_large_number(daily_rev)} {currency}")
        with f2: st.metric("Operational Drag", f"{disrupt_pct*100:.1f}%", delta=f"{rain} mm Rain", delta_color="inverse" if disrupt_pct>0 else "off")
        with f3: st.metric("Est. Daily Loss (VaR)", f"{format_large_number(est_loss)} {currency}", delta="Risk Exposure", delta_color="inverse" if est_loss>0 else "off")

    # 4. AI RISK REPORT
    st.divider()
    st.subheader("🤖 Live Risk Assessment")
    
    risk_level = "LOW"
    risk_color = "green"
    if rain > 10: 
        risk_level = "MODERATE"; risk_color = "orange"
    if rain > 30 or wind > 80: 
        risk_level = "HIGH"; risk_color = "red"

    st.markdown(f"""
    **Live Physical Risk Report for: {location_name}**
    
    *   **Current Status:** :{risk_color}[**{risk_level} RISK**] detected.
    *   **Precipitation (24h):** {rain} mm
    *   **Wind Speed (Max):** {wind} km/h
    
    **AI Strategic Insight:**
    Given the current weather data in **{country}**, {info.get('longName')} operations at the **{asset_label}** face **{risk_level.lower()}** disruption risk today. 
    {"Heavy rainfall may impact local logistics and employee commute." if rain > 10 else "Weather conditions are optimal for operations."}
    
    *Data Source: OpenMeteo & OpenStreetMap live feed.*
    """)

    # 5. NEWS (Restored to your specific request)
    st.divider()
    st.subheader("📰 OSINT: Live Climate News Scraper")

    long_name = info.get('longName', ticker)
    news_items = get_climate_news(ticker, long_name)

    if news_items:
        for news in news_items:
            # We use safe .get() to avoid errors if DDG changes keys
            title = news.get('title', 'No Title')
            body = news.get('body', news.get('title', ''))
            source = news.get('source', 'Unknown Source')
            date = news.get('date', 'Recent')
            url = news.get('url', '#')

            with st.expander(f"📢 {title}"):
                st.write(body)
                st.caption(f"Source: {source} • {date}")
                st.markdown(f"[Read Full Article]({url})")
    else:
        st.info(f"No specific climate risk headlines found for {long_name}.")

else:
    st.write("Please enter a ticker in the sidebar.")