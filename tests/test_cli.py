import datetime as dt
from zoneinfo import ZoneInfo

from weather_notify.cli import (
    collect_afternoon_samples,
    collect_daily_samples,
    format_result,
    overall_ntfy_tag,
    target_date,
)
from weather_notify.ensemble import EnsembleResult

JST = ZoneInfo("Asia/Tokyo")
NOW = dt.datetime(2026, 7, 31, 12, 0, tzinfo=JST)


def test_target_date_morning_and_afternoon_are_today():
    assert target_date("morning", NOW) == dt.date(2026, 7, 31)
    assert target_date("afternoon", NOW) == dt.date(2026, 7, 31)


def test_target_date_evening_is_tomorrow():
    assert target_date("evening", NOW) == dt.date(2026, 8, 1)


def test_collect_daily_samples_filters_by_date_and_merges_sources():
    om_daily = {
        "gfs_seamless": [
            {"date": "2026-07-31", "temp_max": 30.0, "temp_min": 22.0, "pop": 20, "category": "晴れ"},
            {"date": "2026-08-01", "temp_max": 29.0, "temp_min": 21.0, "pop": 60, "category": "雨"},
        ]
    }
    jma_weathers = [("2026-07-31T00:00:00+09:00", "晴れ"), ("2026-08-01T00:00:00+09:00", "雨")]
    jma_pops = [("2026-07-31T06:00:00+09:00", 10.0), ("2026-08-01T06:00:00+09:00", 70.0)]

    samples = collect_daily_samples("morning", om_daily, jma_weathers, jma_pops, NOW)

    sources = {s.source for s in samples}
    assert sources == {"open-meteo:gfs_seamless", "jma:weather", "jma:pop"}
    categories = [s.category for s in samples if s.category]
    assert categories == ["晴れ", "晴れ"]


def test_collect_afternoon_samples_only_uses_hours_from_noon():
    om_hourly = {
        "gfs_seamless": [
            {"time": "2026-07-31T09:00", "temp": 25.0, "pop": 5, "category": "晴れ"},
            {"time": "2026-07-31T13:00", "temp": 31.0, "pop": 40, "category": "くもり"},
            {"time": "2026-07-31T18:00", "temp": 27.0, "pop": 50, "category": "雨"},
            {"time": "2026-08-01T13:00", "temp": 32.0, "pop": 10, "category": "晴れ"},
        ]
    }
    jma_weathers = [("2026-07-31T00:00:00+09:00", "くもり")]
    jma_pops = [
        ("2026-07-31T06:00:00+09:00", 10.0),
        ("2026-07-31T12:00:00+09:00", 30.0),
        ("2026-07-31T18:00:00+09:00", 50.0),
    ]

    samples = collect_afternoon_samples(om_hourly, jma_weathers, jma_pops, NOW)

    om_sample = next(s for s in samples if s.source == "open-meteo:gfs_seamless")
    assert om_sample.temp_max == 31.0
    assert om_sample.temp_min == 27.0
    assert om_sample.pop == 50

    pop_sample = next(s for s in samples if s.source == "jma:pop")
    assert pop_sample.pop == 40.0


def _result(category, confidence="高", pop_avg=20, temp_max_avg=29.0, temp_min_avg=21.0):
    return EnsembleResult(
        category=category,
        category_confidence=confidence,
        category_votes={category: 2},
        pop_avg=pop_avg,
        pop_range=(10, 30),
        temp_max_avg=temp_max_avg,
        temp_max_range=(28.0, 30.0),
        temp_min_avg=temp_min_avg,
        temp_min_range=(20.0, 22.0),
        sample_count=6,
    )


def test_format_result_is_a_single_compact_line():
    line = format_result("中野区", _result("晴れ"))
    assert line == "中野区  ☀️晴れ🟢  ☔20%  🌡29/21℃"


def test_format_result_omits_missing_fields():
    result = _result("くもり", confidence="低", pop_avg=None, temp_max_avg=None, temp_min_avg=None)
    line = format_result("墨田区", result)
    assert line == "墨田区  ☁️くもり🔴"


def test_overall_ntfy_tag_picks_most_severe_category():
    results = [_result("晴れ"), _result("雨")]
    assert overall_ntfy_tag(results) == "rain_cloud"


def test_overall_ntfy_tag_falls_back_to_unknown():
    assert overall_ntfy_tag([]) == "grey_question"
