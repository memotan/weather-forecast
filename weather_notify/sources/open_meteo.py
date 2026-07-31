from typing import Dict, List

import requests

from .. import config
from ..wmo import wmo_code_to_category

DAILY_VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max", "weather_code"]
HOURLY_VARS = ["temperature_2m", "precipitation_probability", "weather_code"]


def fetch(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARS),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": config.TIMEZONE,
        "forecast_days": 3,
        "models": ",".join(config.OPEN_METEO_MODELS),
    }
    response = requests.get(config.OPEN_METEO_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def _series(raw: dict, section: str, var: str, model: str) -> list:
    section_data = raw.get(section) or {}
    values = section_data.get(f"{var}_{model}")
    if values is None:
        # Falls back to the unsuffixed key, in case only one model was requested.
        values = section_data.get(var)
    return values or []


def daily_by_model(raw: dict) -> Dict[str, List[dict]]:
    times = (raw.get("daily") or {}).get("time", [])
    result: Dict[str, List[dict]] = {}
    for model in config.OPEN_METEO_MODELS:
        tmax = _series(raw, "daily", "temperature_2m_max", model)
        tmin = _series(raw, "daily", "temperature_2m_min", model)
        pop = _series(raw, "daily", "precipitation_probability_max", model)
        code = _series(raw, "daily", "weather_code", model)
        entries = []
        for i, date in enumerate(times):
            entries.append(
                {
                    "date": date,
                    "temp_max": tmax[i] if i < len(tmax) else None,
                    "temp_min": tmin[i] if i < len(tmin) else None,
                    "pop": pop[i] if i < len(pop) else None,
                    "category": wmo_code_to_category(code[i]) if i < len(code) else None,
                }
            )
        result[model] = entries
    return result


def hourly_by_model(raw: dict) -> Dict[str, List[dict]]:
    times = (raw.get("hourly") or {}).get("time", [])
    result: Dict[str, List[dict]] = {}
    for model in config.OPEN_METEO_MODELS:
        temp = _series(raw, "hourly", "temperature_2m", model)
        pop = _series(raw, "hourly", "precipitation_probability", model)
        code = _series(raw, "hourly", "weather_code", model)
        entries = []
        for i, time in enumerate(times):
            entries.append(
                {
                    "time": time,
                    "temp": temp[i] if i < len(temp) else None,
                    "pop": pop[i] if i < len(pop) else None,
                    "category": wmo_code_to_category(code[i]) if i < len(code) else None,
                }
            )
        result[model] = entries
    return result
