"""
Upgrade 1: Live Weather Service
Uses OpenWeatherMap if key is present, otherwise falls back to stub.
"""
from dataclasses import dataclass, asdict
import os, sys, requests as _req

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from services.cache_service import cache_get, cache_set

@dataclass
class WeatherReport:
    region: str
    condition: str
    severity: str
    wind_kph: float
    visibility_km: float
    alerts: list

_STUB = {
    "us-west-coast": WeatherReport("us-west-coast", "Wildfires", "HIGH", 45.0, 1.0, ["Air quality warning", "Highway closures"]),
    "us-east-coast": WeatherReport("us-east-coast", "Hurricane", "CRITICAL", 180.0, 0.5, ["Evacuation order", "Port closed"]),
    "southeast-asia": WeatherReport("southeast-asia", "Typhoon", "CRITICAL", 120.0, 1.5, ["Flooding expected"]),
    "europe": WeatherReport("europe", "Heavy Rain", "MEDIUM", 45.0, 5.0, ["Minor flooding"]),
    "middle-east": WeatherReport("middle-east", "Sandstorm", "HIGH", 85.0, 0.5, ["Flights delayed"]),
    "east-asia": WeatherReport("east-asia", "Cloudy", "LOW", 20.0, 8.0, []),
    "north-america": WeatherReport("north-america", "Blizzard", "HIGH", 75.0, 1.2, ["Highway closures", "Airport ground stop"]),
    "latin-america": WeatherReport("latin-america", "Tropical Storm", "HIGH", 80.0, 2.0, ["Port slowdowns", "Mudslide warning"]),
    "south-asia": WeatherReport("south-asia", "Monsoon Flooding", "CRITICAL", 95.0, 0.8, ["Terminal flooded", "Rail suspended"]),
    "oceania": WeatherReport("oceania", "Clear", "LOW", 15.0, 10.0, []),
    "global": WeatherReport("global", "Mixed", "MEDIUM", 30.0, 6.0, []),
}

_REGION_TO_CITY = {
    "us-west-coast": "Los Angeles", "us-east-coast": "New York",
    "europe": "Amsterdam", "southeast-asia": "Singapore",
    "east-asia": "Shanghai", "middle-east": "Dubai",
    "south-asia": "Mumbai", "north-america": "Chicago",
    "latin-america": "Sao Paulo", "oceania": "Sydney",
}

def _calculate_severity(wind_kph: float, condition: str = "") -> str:
    cond = str(condition).lower()
    if any(w in cond for w in ["hurricane", "typhoon", "tornado", "cyclone", "tsunami", "blizzard"]):
        return "CRITICAL"
    if any(w in cond for w in ["severe", "storm", "flood", "sandstorm", "wildfire", "heavy"]):
        return "HIGH"
    if wind_kph > 100: return "CRITICAL"
    if wind_kph > 60: return "HIGH"
    if wind_kph > 30 or any(w in cond for w in ["rain", "snow", "fog", "thunder"]):
        return "MEDIUM"
    return "LOW"

def fetch_weather(region: str) -> WeatherReport:
    key = Config.WEATHER_API_KEY
    city = _REGION_TO_CITY.get(region)
    if key and city:
        cache_key = f"weather_{region}"
        cached = cache_get(cache_key)
        if cached:
            return WeatherReport(**cached)
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": key, "units": "metric"}
            resp = _req.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                wind_kph = round(d.get("wind", {}).get("speed", 0) * 3.6, 1)
                visibility_km = round(d.get("visibility", 10000) / 1000, 1)
                condition = d.get("weather", [{}])[0].get("main", "Clear")
                report = WeatherReport(
                    region=region, condition=condition,
                    severity=_calculate_severity(wind_kph, condition),
                    wind_kph=wind_kph, visibility_km=visibility_km, alerts=[]
                )
                cache_set(cache_key, asdict(report))
                return report
        except Exception as e:
            print(f"[WeatherAPI] Live fetch failed: {e}")
    return _STUB.get(region, WeatherReport(region, "Clear", "LOW", 10.0, 10.0, []))

def get_severe_regions() -> list[str]:
    all_regs = list(_REGION_TO_CITY.keys()) + ["global"]
    severe = set()
    for r in all_regs:
        rep = fetch_weather(r)
        if rep and rep.severity in ["HIGH", "CRITICAL"]:
            severe.add(r)
    for r, w in _STUB.items():
        if w.severity in ["HIGH", "CRITICAL"]:
            severe.add(r)
    return list(severe)