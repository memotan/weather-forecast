"""Maps WMO weather codes (Open-Meteo) and JMA forecast text to a shared category set."""

# Most severe / most actionable first, so mixed forecasts ("晴れ時々雨") resolve
# to the condition worth warning about rather than the more pleasant one.
CATEGORY_ORDER = ("雷雨", "雪", "雨", "霧", "くもり", "晴れ", "不明")

_JMA_KEYWORDS = (
    ("雷雨", "雷"),
    ("雪", "雪"),
    ("雨", "雨"),
    ("霧", "霧"),
    ("くもり", "曇"),
    ("晴れ", "晴"),
)

CATEGORY_EMOJI = {
    "晴れ": "☀️",
    "くもり": "☁️",
    "雨": "🌧️",
    "雪": "❄️",
    "雷雨": "⛈️",
    "霧": "🌫️",
    "不明": "❔",
}

# ntfy "Tags" header accepts emoji shortcodes and renders one next to the title.
CATEGORY_NTFY_TAG = {
    "晴れ": "sunny",
    "くもり": "cloud",
    "雨": "rain_cloud",
    "雪": "snowflake",
    "雷雨": "thunder_cloud_and_rain",
    "霧": "fog",
    "不明": "grey_question",
}


def wmo_code_to_category(code) -> str:
    if code is None:
        return "不明"
    code = int(code)
    if code == 0:
        return "晴れ"
    if code in (1, 2):
        return "晴れ"
    if code == 3:
        return "くもり"
    if code in (45, 48):
        return "霧"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "雨"
    if code in (71, 73, 75, 77, 85, 86):
        return "雪"
    if code in (95, 96, 99):
        return "雷雨"
    return "不明"


def jma_text_to_category(text) -> str:
    if not text:
        return "不明"
    for category, keyword in _JMA_KEYWORDS:
        if keyword in text:
            return category
    return "不明"
