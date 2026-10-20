import pytest

from risk_model import calculate_revenue_at_risk, risk_level, sector_vulnerability

ENERGY = {"totalRevenue": 365_000_000, "sector": "Energy"}  # 1M per day
TECH = {"totalRevenue": 365_000_000, "sector": "Technology"}


def test_calm_weather_has_no_impact():
    daily, at_risk, drag, driver = calculate_revenue_at_risk(ENERGY, rain=5, temp=15)
    assert daily == pytest.approx(1_000_000)
    assert at_risk == 0
    assert drag == 0
    assert driver == "None"


@pytest.mark.parametrize("rain, expected_drag", [(20, 0.0), (20.1, 0.15), (50, 0.15), (50.1, 0.50)])
def test_rain_thresholds_are_strict(rain, expected_drag):
    assert calculate_revenue_at_risk(ENERGY, rain=rain, temp=15)[2] == expected_drag


@pytest.mark.parametrize("temp, expected_drag", [(32, 0.0), (33, 0.08), (41, 0.25)])
def test_heat_thresholds(temp, expected_drag):
    assert calculate_revenue_at_risk(ENERGY, rain=0, temp=temp)[2] == expected_drag


def test_worst_driver_wins():
    _, _, drag, driver = calculate_revenue_at_risk(ENERGY, rain=25, temp=41)
    assert drag == 0.25
    assert driver == "Heat Stress"


def test_sector_weight_scales_impact():
    _, energy_loss, _, _ = calculate_revenue_at_risk(ENERGY, rain=60, temp=15)
    _, tech_loss, _, _ = calculate_revenue_at_risk(TECH, rain=60, temp=15)
    assert energy_loss == pytest.approx(500_000)
    assert tech_loss == pytest.approx(200_000)


@pytest.mark.parametrize("info", [{}, {"totalRevenue": None}, {"totalRevenue": 0}])
def test_missing_revenue_is_explicit_not_zero(info):
    daily, at_risk, _, driver = calculate_revenue_at_risk(info, rain=60, temp=15)
    assert daily is None and at_risk is None
    assert driver == "Revenue unavailable"


def test_unknown_sector_uses_default_weight():
    assert sector_vulnerability(None) == 0.4


@pytest.mark.parametrize("drag, level", [(0, "LOW"), (0.08, "MODERATE"), (0.15, "HIGH")])
def test_risk_level(drag, level):
    assert risk_level(drag) == level
