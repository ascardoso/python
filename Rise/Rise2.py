import requests

lat, lon = 40.7128, -74.0060
url = "https://api.sunrise-sunset.org/json"
params = {
    "lat": lat,
    "lng": lon,
    "date": "today",
    "formatted": 0          # ISO‑8601 UTC times
}

resp = requests.get(url, params=params)
data = resp.json()

# The structure is {"results": {...}, "status":"OK"}
r = data["results"]
sunrise_utc  = r["sunrise"]   # e.g. "2026-10-31T10:32:00+00:00"
sunset_utc   = r["sunset"]
moonrise_utc = r.get("moonrise")
moonset_utc  = r.get("moonset")

print(f"Sunrise (UTC): {sunrise_utc}")
print(f"Moonset  (UTC): {moonset_utc}")

