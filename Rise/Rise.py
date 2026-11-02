#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Open‑Meteo – sorted 24‑hour event list (Pacific Time)

Usage
-----
>>> from open_meteo_sorted import get_open_meteo_times
>>> get_open_meteo_times(40.7128, -74.0060)
[('sunrise', '07:25:00'),
 ('moonset',  '13:29:00'),
 ('moonrise', '22:58:00'),
 ('sunset',   '17:53:00')]
"""

import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Pacific Time – automatically handles DST (PST/PDT)
PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

def _parse_local_iso_to_pacific(iso_str: str) -> datetime:
    """
    Convert a naive ISO string (e.g. "2026-10-31T07:25") to a timezone‑aware
    datetime in Pacific Time.
    """
    # The string is naive; attach the requested timezone first
    dt_naive = datetime.fromisoformat(iso_str)
    return dt_naive.replace(tzinfo=PACIFIC_TZ)

def get_open_meteo_times(lat: float, lon: float) -> list[tuple[str, str]]:
    """
    Query Open‑Meteo for the given latitude/longitude and return a
    *sorted* list of (event, "HH:MM:SS") tuples in Pacific Time.

    Parameters
    ----------
    lat : float
        Latitude of the location.
    lon : float
        Longitude of the location.

    Returns
    -------
    list[tuple[str, str]]
        Sorted by event time.  Example:
            [('sunrise', '07:25:00'),
             ('moonset',  '13:29:00'),
             ('moonrise', '22:58:00'),
             ('sunset',   '17:53:00')]
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":  lat,
        "longitude": lon,
        # Return all four events for the current day
        "daily":     "sunrise,sunset,moonrise,moonset",
        # We want the times in Pacific Time (PST/PDT)
        "timezone":  "America/Los_Angeles",
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    # Safety check – Open‑Meteo may return an error
    if "daily" not in data:
        raise RuntimeError(f"Unexpected Open‑Meteo response: {data}")

    daily = data["daily"]

    # Build a list of (event_name, datetime) tuples
    events = []
    for event in ["sunrise", "sunset", "moonrise", "moonset"]:
        vals = daily.get(event)
        if not vals or not vals[0]:
            continue  # Skip missing events (e.g. polar night)
        dt_pacific = _parse_local_iso_to_pacific(vals[0])
        events.append((event, dt_pacific))

    # Sort by the datetime value
    events.sort(key=lambda x: x[1])

    # Return a list of (event, "HH:MM:SS") strings
    return [(name, dt.strftime("%H:%M:%S")) for name, dt in events]


# --------------------------------------------------------------------------- #
# Demo – replace the latitude/longitude with your own location
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Example: New York City (40.7128° N, 74.0060° W)
    lat, lon = 40.7128, -74.0060

    try:
        sorted_events = get_open_meteo_times(lat, lon)
        print("Open‑Meteo – sorted 24‑hour events (Pacific Time):")
        for name, time_str in sorted_events:
            print(f"  {name:8s} → {time_str}")
    except Exception as exc:
        print(f"Error: {exc}")

