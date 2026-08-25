from typing import Iterator, List, Tuple

from .. import config
from ..http_client import get_json
from ..wmo import jma_text_to_category


def fetch_forecast(office_code: str) -> list:
    url = config.JMA_FORECAST_URL.format(office_code=office_code)
    return get_json(url)


def fetch_overview(office_code: str) -> str:
    url = config.JMA_OVERVIEW_URL.format(office_code=office_code)
    return get_json(url).get("text", "")


def _iter_time_series(data: list) -> Iterator[dict]:
    for block in data:
        for series in block.get("timeSeries", []):
            yield series


def extract_weathers(data: list, area_code: str) -> List[Tuple[str, str]]:
    """Returns (timeDefine, category) pairs for the area's textual weather forecast."""
    results = []
    for series in _iter_time_series(data):
        time_defines = series.get("timeDefines", [])
        for area in series.get("areas", []):
            if area.get("area", {}).get("code") != area_code:
                continue
            weathers = area.get("weathers")
            if not weathers:
                continue
            for time_str, text in zip(time_defines, weathers):
                results.append((time_str, jma_text_to_category(text)))
    return results


def extract_pops(data: list, area_code: str) -> List[Tuple[str, float]]:
    """Returns (timeDefine, probability-of-precipitation) pairs for the area."""
    results = []
    for series in _iter_time_series(data):
        time_defines = series.get("timeDefines", [])
        for area in series.get("areas", []):
            if area.get("area", {}).get("code") != area_code:
                continue
            pops = area.get("pops")
            if not pops:
                continue
            for time_str, value in zip(time_defines, pops):
                if value in (None, ""):
                    continue
                try:
                    results.append((time_str, float(value)))
                except ValueError:
                    continue
    return results
