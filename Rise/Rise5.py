import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def get_astro_times_with_zones(url: str, params: dict) -> dict:
    r = requests.get(url, params=params).json()
    
    def to_local(utc_str):
        if not utc_str:
            return None
        utc_dt = datetime.fromisoformat(utc_str)
        local_dt = utc_dt.astimezone(ZoneInfo('America/New_York'))
        return local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # Sunrise‑Sunset.org – always UTC
    if "results" in r:
        res = r["results"]
        return {
            "sunrise_utc":  res.get("sunrise"),
            "sunset_utc":   res.get("sunset"),
            "moonrise_utc": res.get("moonrise"),
            "moonset_utc":  res.get("moonset"),
            # Local conversions
            "sunrise_local":  to_local(res.get("sunrise")),
            "sunset_local":   to_local(res.get("sunset")),
            "moonrise_local": to_local(res.get("moonrise")),
            "moonset_local":  to_local(res.get("moonset"))
        }
    
    # Open‑Meteo – already local, but we’ll also add UTC
    if "daily" in r:
        d = r["daily"]
        # Build ISO‑8601 strings with UTC offset +00:00
        def iso_local_to_utc(local_str):
            if not local_str:
                return None
            # local_str is like "2026-10-31T07:25"
            dt = datetime.fromisoformat(local_str)
            # attach the requested timezone
            tz = ZoneInfo('America/New_York')
            dt_local = tz.localize(dt) if hasattr(tz, 'localize') else dt.replace(tzinfo=tz)
            # convert to UTC
            dt_utc = dt_local.astimezone(timezone.utc)
            return dt_utc.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        
        return {
            "sunrise_local":  d["sunrise"][0] if d.get("sunrise") else None,
            "sunset_local":   d["sunset"][0]  if d.get("sunset") else None,
            "moonrise_local": d["moonrise"][0] if d.get("moonrise") else None,
            "moonset_local":  d["moonset"][0]  if d.get("moonset") else None,
            "sunrise_utc":  iso_local_to_utc(d["sunrise"][0] if d.get("sunrise") else None),
            "sunset_utc":   iso_local_to_utc(d["sunset"][0]  if d.get("sunset") else None),
            "moonrise_utc": iso_local_to_utc(d["moonrise"][0] if d.get("moonrise") else None),
            "moonset_utc":  iso_local_to_utc(d["moonset"][0]  if d.get("moonset") else None),
        }
    
    raise ValueError(f"Unexpected response format: {r}")

# ----- Example usage -------------------------------------------------
url_ss = "https://api.sunrise-sunset.org/json"
params_ss = {"lat": 40.7128, "lng": -74.0060, "date": "today", "formatted": 0}
print("Sunrise‑Sunset.org →", get_astro_times_with_zones(url_ss, params_ss))

url_meteo = "https://api.open-meteo.com/v1/forecast"
params_meteo = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "daily": "sunrise,sunset,moonrise,moonset",
    "timezone": "America/New_York"
}
print("Open‑Meteo →", get_astro_times_with_zones(url_meteo, params_meteo))

