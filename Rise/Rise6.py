#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------- #
# Helpers – all times will be rendered in 24‑hour format, Pacific Time zone.
# --------------------------------------------------------------------------- #
PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

def to_pst(utc_iso: str | None) -> str | None:
    """
    Convert a UTC ISO‑8601 string to Pacific Time (24‑hour format).
    Returns e.g. '2026-11-01 03:26:36' (PST/PDT depending on the date).
    """
    if not utc_iso:
        return None
    # Parse the ISO string (includes UTC offset)
    utc_dt = datetime.fromisoformat(utc_iso)
    # Convert to Pacific
    pst_dt = utc_dt.astimezone(PACIFIC_TZ)
    return pst_dt.strftime("%Y-%m-%d %H:%M:%S")   # 24‑hour, no TZ abbreviation

def iso_local_to_utc(local_iso: str | None) -> str | None:
    """
    Convert a local ISO‑8601 string (no offset) to UTC in ISO format.
    Used for the Open‑Meteo data, which is returned without an offset.
    """
    if not local_iso:
        return None
    # Parse the naive datetime (assumes it is in PACIFIC_TZ)
    local_dt = datetime.fromisoformat(local_iso).replace(tzinfo=PACIFIC_TZ)
    utc_dt = local_dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

# --------------------------------------------------------------------------- #
# Main wrapper – identical logic to before, but all times are Pacific.
# --------------------------------------------------------------------------- #
def get_astro_times_with_zones(url: str, params: dict) -> dict:
    r = requests.get(url, params=params).json()

    # ---------- Sunrise‑Sunset.org  (always UTC) ----------
    if "results" in r:
        res = r["results"]
        return {
            # UTC values
            "sunrise_utc":  res.get("sunrise"),
            "sunset_utc":   res.get("sunset"),
            "moonrise_utc": res.get("moonrise"),
            "moonset_utc":  res.get("moonset"),

            # Pacific Time, 24‑hour format
            "sunrise_pst":  to_pst(res.get("sunrise")),
            "sunset_pst":   to_pst(res.get("sunset")),
            "moonrise_pst": to_pst(res.get("moonrise")),
            "moonset_pst":  to_pst(res.get("moonset"))
        }

    # ---------- Open‑Meteo (returns local times) ----------
    if "daily" in r:
        d = r["daily"]
        # We request the data for Pacific Time; all local values are already PST/PDT.
        return {
            # Local (Pacific) – 24‑hour format
            "sunrise_pst": d["sunrise"][0] if d.get("sunrise") else None,
            "sunset_pst":  d["sunset"][0]  if d.get("sunset") else None,
            "moonrise_pst": d["moonrise"][0] if d.get("moonrise") else None,
            "moonset_pst":  d["moonset"][0]  if d.get("moonset") else None,

            # UTC values (converted from the local strings)
            "sunrise_utc":  iso_local_to_utc(d["sunrise"][0] if d.get("sunrise") else None),
            "sunset_utc":   iso_local_to_utc(d["sunset"][0]  if d.get("sunset") else None),
            "moonrise_utc": iso_local_to_utc(d["moonrise"][0] if d.get("moonrise") else None),
            "moonset_utc":  iso_local_to_utc(d["moonset"][0]  if d.get("moonset") else None),
        }

    raise ValueError(f"Unexpected response format: {r}")

# --------------------------------------------------------------------------- #
# Example usage – change latitude/longitude to your location.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # 1️⃣ Sunrise‑Sunset.org (UTC → PST)
    url_ss = "https://api.sunrise-sunset.org/json"
    params_ss = {"lat": 40.7128, "lng": -74.0060,
                 "date": "today", "formatted": 0}
    print("Sunrise‑Sunset.org →")
    print(get_astro_times_with_zones(url_ss, params_ss))
    print()

    # 2️⃣ Open‑Meteo – request data for Pacific Time
    url_meteo = "https://api.open-meteo.com/v1/forecast"
    params_meteo = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "daily": "sunrise,sunset,moonrise,moonset",
        "timezone": "America/Los_Angeles"   # <-- Pacific
    }
    print("Open‑Meteo →")
    print(get_astro_times_with_zones(url_meteo, params_meteo))

