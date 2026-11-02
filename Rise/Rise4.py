import requests
from datetime import datetime
import pytz  # pip install pytz

def get_astro_times(url: str, params: dict) -> dict:
    """Return a dict with keys 'sunrise', 'sunset', 'moonrise', 'moonset'.
       Times are returned as ISO‑8601 strings in the requested timezone."""
    resp = requests.get(url, params=params)
    data = resp.json()

    # --------- Sunrise‑Sunset.org ---------------------------------
    if "results" in data:
        r = data["results"]
        return {
            "sunrise": r.get("sunrise"),
            "sunset":  r.get("sunset"),
            "moonrise": r.get("moonrise"),
            "moonset":  r.get("moonset")
        }

    # --------- Open‑Meteo ----------------------------------------
    if "daily" in data:
        d = data["daily"]
        return {
            # Each list contains a single string; pick the first element
            "sunrise":  d["sunrise"][0] if d.get("sunrise") else None,
            "sunset":   d["sunset"][0]  if d.get("sunset") else None,
            "moonrise": d["moonrise"][0] if d.get("moonrise") else None,
            "moonset":  d["moonset"][0]  if d.get("moonset") else None
        }

    raise ValueError(f"Unexpected response format: {data}")

# -----------------------------------------------------------------

# Example 1: Sunrise‑Sunset.org (UTC)
url = "https://api.sunrise-sunset.org/json"
params = {
    "lat": 40.7128,
    "lng": -74.0060,
    "date": "today",
    "formatted": 0
}
print("Sunrise‑Sunset.org →", get_astro_times(url, params))

# Example 2: Open‑Meteo (local time)
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "daily": "sunrise,sunset,moonrise,moonset",
    "timezone": "America/New_York"
}
print("Open‑Meteo (local) →", get_astro_times(url, params))

