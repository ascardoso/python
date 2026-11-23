import requests

lat, lon = 36.9872, -121.9348
point_url = f"https://api.weather.gov/points/{lat},{lon}"
resp = requests.get(point_url).json()

# 8‑day forecast
forecast = requests.get(resp['properties']['forecast']).json()

# Hourly forecast
hourly  = requests.get(resp['properties']['forecastHourly']).json()

# Stations that report for this grid
stations = requests.get(resp['properties']['observationStations']).json()

# Forecast zone polygon
zone_geo = requests.get(resp['properties']['forecastZone']).json()

print ("Forecast=")
print (forecast)
print ("--------------------------------")
#print ("Hourly=")
#print (hourly)
#print ("--------------------------------")
#print ("Stations=")
#print (stations)
#print ("--------------------------------")
#print ("Zone_geo=")
#print (zone_geo)


# Extract the first 10 forecast periods (5 days)
periods = forecast['properties']['periods'][:10]

for period in periods:
    print("----------------------------")
    print("Date:", period['startTime'][:10])
    print("Period:", period['name'])
    print("Temperature:", period['temperature'],
          period['temperatureUnit'])
    print("Conditions:", period['shortForecast'])
    print("Wind:", period['windSpeed'],
          period['windDirection'])

    rain = period['probabilityOfPrecipitation']['value']
    print("Chance of rain:", rain, "%")


print ("-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-4-")

# Get the first 10 forecast periods (approximately 5 days)
periods = forecast['properties']['periods'][:10]

# Group daytime and nighttime forecasts by date
daily_forecast = {}

for period in periods:
    date = period['startTime'][:10]

    if date not in daily_forecast:
        daily_forecast[date] = {
            'date': date,
            'high': None,
            'low': None,
            'conditions': None,
            'wind': None,
            'rain_chance': None
        }

    if period['isDaytime']:
        daily_forecast[date]['high'] = period['temperature']
        daily_forecast[date]['conditions'] = period['shortForecast']
        daily_forecast[date]['wind'] = (
            period['windSpeed'] + ' ' + period['windDirection']
        )
        daily_forecast[date]['rain_chance'] = (
            period['probabilityOfPrecipitation']['value']
        )
    else:
        daily_forecast[date]['low'] = period['temperature']

# Display the 5-day forecast
for day in daily_forecast.values():
    print("------------------------------")
    print("Date:", day['date'])
    print("High:", day['high'], "°F")
    print("Low:", day['low'], "°F")
    print("Conditions:", day['conditions'])
    print("Wind:", day['wind'])
    print("Rain Chance:", day['rain_chance'], "%")

