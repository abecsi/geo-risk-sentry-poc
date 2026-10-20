"""Illustrative revenue-at-risk heuristic, kept separate from the UI so it can be unit tested.

Not a calibrated or validated model: step-function thresholds and fixed sector weights.
"""

MODEL_VERSION = "0.2.0"

# (threshold, operational drag) pairs, checked from most to least severe
RAIN_THRESHOLDS_MM = [(50, 0.50), (20, 0.15)]
HEAT_THRESHOLDS_C = [(40, 0.25), (32, 0.08)]  # Assumed thermal stress on efficiency

HIGH_VULNERABILITY_SECTORS = ["Energy", "Materials", "Utilities"]
HIGH_VULNERABILITY_WEIGHT = 1.0
DEFAULT_VULNERABILITY_WEIGHT = 0.4


def _step_drag(value, thresholds):
    for threshold, drag in thresholds:
        if value > threshold:
            return drag
    return 0.0


def sector_vulnerability(sector):
    sector = sector or "Unknown"
    if any(x in sector for x in HIGH_VULNERABILITY_SECTORS):
        return HIGH_VULNERABILITY_WEIGHT
    return DEFAULT_VULNERABILITY_WEIGHT


def calculate_revenue_at_risk(info, rain, temp):
    """Returns (daily_revenue, revenue_at_risk, drag, driver); revenue values are None if revenue is missing."""
    revenue = info.get('totalRevenue')
    if not revenue:
        return None, None, 0.0, "Revenue unavailable"
    daily_rev = revenue / 365

    rain_drag = _step_drag(rain, RAIN_THRESHOLDS_MM)
    heat_drag = _step_drag(temp, HEAT_THRESHOLDS_C)

    disruption = max(rain_drag, heat_drag)
    driver = "Heat Stress" if heat_drag > rain_drag else "Precipitation"
    if disruption == 0: driver = "None"

    return daily_rev, daily_rev * sector_vulnerability(info.get('sector')) * disruption, disruption, driver


def risk_level(drag):
    return "HIGH" if drag > 0.1 else ("MODERATE" if drag > 0 else "LOW")
