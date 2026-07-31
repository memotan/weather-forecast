from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float
    jma_office_code: str
    jma_area_code: str


LOCATIONS = [
    Location("日野市", 35.6711, 139.3949, "130000", "130010"),
    Location("墨田区", 35.7106, 139.8015, "130000", "130010"),
]

# Open-Meteo model ensemble: independent providers (JP, US, EU, DE) with no API key required.
OPEN_METEO_MODELS = ["jma_seamless", "gfs_seamless", "icon_seamless", "ecmwf_ifs04"]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

JMA_FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{office_code}.json"
JMA_OVERVIEW_URL = "https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{office_code}.json"

TIMEZONE = "Asia/Tokyo"

WINDOWS = ("morning", "afternoon", "evening")
