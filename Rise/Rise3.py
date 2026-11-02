import requests

def get_astro_times(url: str, params: dict) -> dict:
    """Return a dict with keys 'sunrise', 'sunset', 'moonrise', 'moonset'."""
    resp = requests.get(url, params=params)
    data = resp.json()

    # Handle the two common shapes
    if "results" in data:          # Sunrise‑Sunset.org
        r = data["results"]
    elif "daily" in data:          # Open‑Meteo
        r = {
            "sunrise":  data["daily"]["sunrise_sunset"][0][0],
            "sunset":   data["daily"]["sunrise_sunset"][0][1],
            "moonrise": data["daily"]["moonrise_moonset"][0][0],
            "moonset":  data["daily"]["moonrise_moonset"][0][1]
        }
    else:
        raise ValueError(f"Unexpected response format: {data}")

    return r

# Example usage
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "daily": "sunrise_sunset,moonrise_moonset",
    "timezone": "America/New_York"
}
times = get_astro_times(url, params)
print(times)

