import requests

lat, lon = 40.7128, -74.0060
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": lat,
    "longitude": lon,
    "daily": "sunrise_sunset,moonrise_moonset",
    "timezone": "America/New_York"
}

resp = requests.get(url, params=params)
data = resp.json()

sunrise, sunset = data["daily"]["sunrise_sunset"][0]
moonrise, moonset = data["daily"]["moonrise_moonset"][0]

print(f"Sunrise: {sunrise}")
print(f"Moonset : {moonset}")

