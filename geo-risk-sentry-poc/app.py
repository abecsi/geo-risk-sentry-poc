import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from geopy.geocoders import Nominatim
from duckduckgo_search import DDGS

# --- PROPRIETARY ASSET DATABASE (DEMO TIER) ---
# In a real startup, this would be a SQL Database or API call to Verisk/Bloomberg.
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
        "NOVN.SW": { # Novartis
        "Factory": {"name": "Stein Sterile Manufacturing Site", "lat": 47.5422, "lon": 7.9536},
        "Logistics": {"name": "Basel Campus Supply Hub", "lat": 47.5623, "lon": 7.5756}
    },
    "NESN.SW": { # Nestlé
        "Factory": {"name": "Nespresso Production Centre (Orbe)", "lat": 46.7237, "lon": 6.5362},
        "Logistics": {"name": "Distribution Center Avenches", "lat": 46.8800, "lon": 7.0400}
    }
}

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Geo-Risk Sentry", page_icon="🌍", layout="wide")

# --- 2. FALLBACK DATA (The "Safety Net") ---
DEMO_DATA = {
    "EQNR": {
        "longName": "Equinor ASA",
        "sector": "Energy",
        "marketCap": 75_000_000_000,
        "currency": "USD",
        "city": "Stavanger",
        "country": "Norway",
        "totalRevenue": 100_000_000_000
    },
    "NHY.OL": {
        "longName": "Norsk Hydro ASA",
        "sector": "Basic Materials",
        "marketCap": 130_000_000_000,
        "currency": "NOK",
        "city": "Oslo",
        "country": "Norway",
        "totalRevenue": 150_000_000_000
    },
    "TSLA": {
        "longName": "Tesla, Inc.",
        "sector": "Consumer Cyclical",
        "marketCap": 750_000_000_000,
        "currency": "USD",
        "city": "Austin",
        "country": "United States",
        "totalRevenue": 96_000_000_000
    },
    "ASML": {
        "longName": "ASML Holding N.V.",
        "sector": "Technology",
        "marketCap": 350_000_000_000,
        "currency": "EUR",
        "city": "Veldhoven",
        "country": "Netherlands",
        "totalRevenue": 27_000_000_000
    },
    # --- SWISS TICKERS ---
    "NESN.SW": {
        "longName": "Nestlé S.A.",
        "sector": "Consumer Defensive",
        "marketCap": 260_000_000_000,
        "currency": "CHF",
        "city": "Vevey",
        "country": "Switzerland",
        "totalRevenue": 93_000_000_000
    },
    "NOVN.SW": {
        "longName": "Novartis AG",
        "sector": "Healthcare",
        "marketCap": 200_000_000_000,
        "currency": "CHF",
        "city": "Basel",
        "country": "Switzerland",
        "totalRevenue": 45_000_000_000
    }
}

# --- 3. ROBUST DATA FETCHER ---
def get_stock_data_safe(ticker):
    """
    1. Tries to fetch LIVE data using the exact ticker (e.g. "NESN.SW").
    2. If that fails (Network/SSL), looks for the exact ticker in DEMO_DATA.
    """
    try:
        # 1. LIVE FETCH (Use full ticker with extension)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Validation check: if longName is missing, the fetch likely failed silently
        if 'longName' not in info:
            raise ValueError("Empty Data returned from API")
            
        return stock, info, False # Success, Real Data
        
    except Exception as e:
        # 2. FALLBACK LOGIC
        # Check if the exact ticker exists in our Demo DB
        if ticker in DEMO_DATA:
            return None, DEMO_DATA[ticker], True # Using Fallback
        
        # Optional: specific handling for Oslo if user forgot .OL
        # If user typed "NHY" but we only have "NHY.OL" in demo, we can try to find it
        # (This is just a helper for the demo experience)
        for demo_ticker in DEMO_DATA:
            if ticker in demo_ticker: 
                return None, DEMO_DATA[demo_ticker], True

        # 3. TOTAL FAILURE
        return None, {
            "longName": ticker, "sector": "Unknown", "marketCap": 0, 
            "currency": "N/A", "city": "Unknown", "country": "Unknown", "totalRevenue": 0
        }, True
        
# --- HELPER FUNCTIONS ---

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

def get_real_esg_score(stock_object):
    """
    Fetches real Sustainalytics data via yfinance.
    Returns: Score (Float) and Rating Label (String)
    """
    try:
        # Fetch the sustainability dataframe
        sus_df = stock_object.sustainability
        
        if sus_df is not None and not sus_df.empty:
            # Extract Total ESG Risk Score
            total_score = sus_df.loc['totalEsg', 'esgScores']
            
            # Convert Number to Label (Sustainalytics Methodology)
            if total_score < 10: label = "Negligible Risk (Top)"
            elif total_score < 20: label = "Low Risk (Good)"
            elif total_score < 30: label = "Medium Risk"
            elif total_score < 40: label = "High Risk"
            else: label = "Severe Risk"
            
            return total_score, label
    except Exception as e:
        pass
    
    return None, None

def get_live_weather_risk(lat, lon):
    """Fetches real-time rain data from Open-Meteo API"""
    try:
        # API call for precipitation (rain) forecast
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,windspeed_10m_max&timezone=auto"
        response = requests.get(url).json()
        
        # Get today's rain amount
        rain_today = response['daily']['precipitation_sum'][0] # in mm
        wind_today = response['daily']['windspeed_10m_max'][0] # in km/h
        return rain_today, wind_today
    except:
        return 0, 0

def get_climate_news(ticker, company_name):
    """
    Searches for NEWS articles only (bypassing general web pages).
    """
    results = []
    
    # 1. ENTITY MAPPING
    mappings = {
        "GOOG": "Google",
        "GOOGL": "Google",
        "META": "Facebook",
        "BRK-B": "Berkshire Hathaway",
        "EQNR": "Equinor",
        "NHY.OL": "Norsk Hydro"
    }
    
    if ticker in mappings:
        search_term = mappings[ticker]
    else:
        search_term = company_name.replace("Inc.", "").replace("Corp.", "").replace("PLC", "").replace("Ltd.", "").strip()

    # 2. STRICT NEWS QUERY
    # We remove the complex (OR) logic and keep it simple for the News engine
    query = f'"{search_term}" climate risk supply chain environment'
    
    try:
        with DDGS() as ddgs:
            # 3. USE .news() INSTEAD OF .text()
            # region="us-en": Forces English results even if you are in Norway
            # safesearch="moderate": Blocks adult content
            # max_results=3: Keeps it fast
            ddgs_news = ddgs.news(query, region="us-en", safesearch="moderate", max_results=3)
            
            for r in ddgs_news:
                results.append(r)
                
    except Exception as e:
        print(f"News error: {e}")
        
    return results

def calculate_revenue_at_risk(info, rain_mm):
    """
    Calculates estimated daily financial loss based on Sector Vulnerability and Weather Severity.
    """
    # 1. Get Real Revenue (TTM)
    revenue = info.get('totalRevenue')
    
    # Fallback if Yahoo data is missing (common for smaller caps)
    if revenue is None:
        return None, None, None

    daily_revenue = revenue / 365

    # 2. Sector Vulnerability Factor (The "Quant" Logic)
    # How much does physical disruption impact operations?
    # Energy/Manufacturing = High (Factories stop)
    # Tech/Services = Low (Remote work possible)
    sector = info.get('sector', 'Unknown')
    
    if any(x in sector for x in ['Energy', 'Basic Materials', 'Industrials', 'Utilities']):
        vulnerability = 1.0  # 100% operational reliance on physical assets
    elif any(x in sector for x in ['Technology', 'Communication', 'Financial']):
        vulnerability = 0.3  # 30% reliance (Data centers, offices)
    else:
        vulnerability = 0.5  # Standard consumer goods/healthcare

    # 3. Weather Severity Factor (Parametric Trigger)
    # If rain > 50mm, we assume significant slowdown.
    if rain_mm >= 50:
        disruption_pct = 0.50 # 50% capacity loss
    elif rain_mm >= 20:
        disruption_pct = 0.15 # 15% capacity loss (slowdown)
    elif rain_mm >= 5:
        disruption_pct = 0.02 # 2% friction cost
    else:
        disruption_pct = 0.0  # Business as usual

    # 4. The Calculation
    estimated_loss = daily_revenue * vulnerability * disruption_pct
    
    return daily_revenue, estimated_loss, disruption_pct

# --- TITLE ---
st.title("🌍 Geo-Risk Sentry: AI-Driven Asset Analysis")
st.markdown("### Physical Risk & ESG Intelligence Dashboard")

# --- SIDEBAR ---

with st.sidebar:
    st.header("Asset Selection")
    # Add the tickers from our DB to the hint so users know what works best
    ticker = st.text_input("Enter Stock Ticker:", "EQNR")
    st.caption("✨ Best Data coverage: TSLA, NHY.OL, ASML, SHELL, EQNR, NOVN.SW, NESN.SW")
    
    st.divider()
    
    # ASSET TYPE SELECTOR
    asset_type = st.selectbox(
        "Select Asset Layer:",
        ["Headquarters (Corporate)", "Primary Factory (Manufacturing)", "Supply Chain Hub (Logistics)"]
    )
if ticker:
    try:
        # --- 1. FETCH FINANCIAL DATA (ROBUST) ---
        # We use the new safe function instead of calling yf.Ticker directly
        stock, info, is_fallback = get_stock_data_safe(ticker)
        
        if is_fallback:
            st.warning(f"⚠️ Network Connection Issue to Yahoo Finance. Using Cached Demo Data for {ticker}.")
        
        # --- 2. EXTRACT LOCATION (DEFAULTS) ---
        city = info.get('city', 'Unknown')
        country = info.get('country', 'Unknown')
        
        # Default: Use the Dynamic HQ Lookup
        lat, lon = get_coordinates(city, country)
        location_name = f"{city} (HQ)" 
        asset_label = "corporate headquarters" # Default description
        is_exact_match = False

        # --- 3. OVERRIDE: CHECK PROPRIETARY DB ---
        if ticker in ASSET_DB:
            if asset_type == "Primary Factory (Manufacturing)":
                lat = ASSET_DB[ticker]["Factory"]["lat"]
                lon = ASSET_DB[ticker]["Factory"]["lon"]
                location_name = ASSET_DB[ticker]["Factory"]["name"]
                asset_label = "primary manufacturing facility" # <--- UPDATES HERE
                is_exact_match = True
                
            elif asset_type == "Supply Chain Hub (Logistics)":
                lat = ASSET_DB[ticker]["Logistics"]["lat"]
                lon = ASSET_DB[ticker]["Logistics"]["lon"]
                location_name = ASSET_DB[ticker]["Logistics"]["name"]
                asset_label = "logistics and supply chain hub" # <--- UPDATES HERE
                is_exact_match = True

        # Fallback Logic
        if asset_type != "Headquarters (Corporate)" and not is_exact_match:
            st.warning(f"⚠️ Precise {asset_type} data not available for {ticker}. Showing regional HQ risk as proxy.")

        # --- 4. FETCH REAL RISK DATA (Weather) ---
        if lat:
            rain, wind = get_live_weather_risk(lat, lon)
        else:
            rain, wind = 0, 0
            lat, lon = 59.91, 10.75 # Fallback coordinates

        # --- 5. DISPLAY KEY METRICS ---
        st.subheader(f"📊 Analysis: {info.get('longName', ticker.upper())}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        currency = info.get('currency', 'USD')
        formatted_mcap = f"{format_large_number(info.get('marketCap'))} {currency}"
        
        # Real ESG Score Logic
        raw_esg_score, esg_label = get_real_esg_score(stock)
        if raw_esg_score:
            esg_display = f"{raw_esg_score:.1f}"
            esg_comment = esg_label
            is_real_esg = True
        else:
            esg_display = "N/A"
            esg_comment = "Data Unavailable"
            is_real_esg = False

        with col1: st.metric("Sector", info.get('sector', 'Unknown'))
        with col2: st.metric("Market Cap", formatted_mcap)
        with col3: st.metric("HQ Location", f"{city}, {country}")
        
        with col4:
            st.metric("Sustainalytics Score", esg_display, delta=esg_comment, delta_color="inverse")
            if is_real_esg:
                st.caption("✅ Real-time Sustainalytics Data")
            else:
                st.caption("⚠️ Real ESG data unavailable via API.")

        # --- 6. DYNAMIC MAP (DEFAULT STREAMLIT MAP) ---
        st.divider()
        st.subheader(f"📍 Real-Time Asset Monitor: {location_name}")
        
        if is_exact_match:
            st.success(f"✅ Verified Asset Coordinates Found: **{location_name}**")
        
        # Create the dataframe
        # We add a 'size' column to make the dot look like a "Risk Radius"
        map_df = pd.DataFrame({
            'lat': [lat], 
            'lon': [lon], 
            'size': [500] # Relative size for the dot
        })
        
        # Render the map
        # This uses Streamlit's internal token, so it works 100% of the time.
        st.map(map_df, zoom=10, size='size')
        
        # --- 7. FINANCIAL IMPACT MODEL ---
        st.divider()
        st.subheader("💰 Parametric Revenue-at-Risk Model")
        daily_rev, est_loss, disrupt_pct = calculate_revenue_at_risk(info, rain)
        
        if daily_rev:
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: st.metric("Daily Revenue (TTM)", f"{format_large_number(daily_rev)} {currency}")
            with f_col2: st.metric("Operational Drag", f"{disrupt_pct*100:.1f}%", f"{rain} mm Rain", delta_color="inverse")
            with f_col3: st.metric("Est. Daily Loss (VaR)", f"{format_large_number(est_loss)} {currency}", "Risk Exposure", delta_color="inverse")
            
            if est_loss > 0:
                st.warning(f"⚠️ Financial Alert: Current weather conditions in {location_name} are estimated to impact daily turnover by **{format_large_number(est_loss)}**. This assumes a **{info.get('sector')}** sector vulnerability profile.")
            else:
                st.success(f"✅ Low Risk: Current weather conditions are within safe operational limits for {info.get('longName')}.")

        # --- 8. AI RISK ASSESSMENT REPORT ---
        st.divider()
        st.subheader("🤖 Live Risk Assessment")
        
        # Logic to determine risk status
        risk_level = "LOW"
        risk_color = "green"
        if rain > 10: 
            risk_level = "MODERATE"
            risk_color = "orange"
        if rain > 30 or wind > 80: 
            risk_level = "HIGH"
            risk_color = "red"

         # --- 9. NEWS SCRAPER (DDG) ---
        st.divider()
        st.subheader("📰 OSINT: Live Climate News Scraper")

        long_name = info.get('longName', ticker)
        news_items = get_climate_news(ticker, long_name)

        if news_items:
            for news in news_items:
                # The .news() dictionary keys are 'title', 'body', 'url', 'source', 'date'
                with st.expander(f"📢 {news['title']}"):
                    st.write(news['body'])
                    
                    # Professional Footer with Source and Date
                    st.caption(f"Source: {news['source']} • {news['date']}")
                    st.markdown(f"[Read Full Article]({news['url']})")
        else:
            st.info(f"No specific climate risk headlines found for {long_name} in the past year.")

        # Final Report
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

    except Exception as e:
        st.error(f"Error analyzing {ticker}: {e}")
else:
    st.write("Enter a ticker to begin.")