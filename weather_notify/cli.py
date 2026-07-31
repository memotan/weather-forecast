import argparse
import datetime as dt
import os
from collections import Counter
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

from . import config
from .ensemble import EnsembleResult, Sample, summarize
from .notify import send_ntfy
from .sources import jma, open_meteo
from .wmo import CATEGORY_EMOJI, CATEGORY_NTFY_TAG, CATEGORY_ORDER

JST = ZoneInfo("Asia/Tokyo")

WINDOW_TITLES = {
    "morning": "本日の天気予報",
    "afternoon": "本日午後〜夜の天気予報",
    "evening": "明日の天気予報",
}

CONFIDENCE_EMOJI = {"高": "👍", "中": "🤝", "低": "❓"}


def target_date(window: str, now: dt.datetime) -> dt.date:
    if window == "evening":
        return (now + dt.timedelta(days=1)).date()
    return now.date()


def _jma_samples_for_date(jma_weathers, jma_pops, date: dt.date) -> List[Sample]:
    samples = []
    for time_str, category in jma_weathers:
        if dt.datetime.fromisoformat(time_str).astimezone(JST).date() == date:
            samples.append(Sample(source="jma:weather", category=category))
    matching_pops = [
        pop
        for time_str, pop in jma_pops
        if dt.datetime.fromisoformat(time_str).astimezone(JST).date() == date
    ]
    if matching_pops:
        samples.append(Sample(source="jma:pop", pop=sum(matching_pops) / len(matching_pops)))
    return samples


def collect_daily_samples(
    window: str,
    om_daily: Dict[str, List[dict]],
    jma_weathers: List[Tuple[str, str]],
    jma_pops: List[Tuple[str, float]],
    now: dt.datetime,
) -> List[Sample]:
    date = target_date(window, now)
    date_str = date.isoformat()
    samples = []
    for model, entries in om_daily.items():
        for entry in entries:
            if entry["date"] == date_str:
                samples.append(
                    Sample(
                        source=f"open-meteo:{model}",
                        category=entry["category"],
                        pop=entry["pop"],
                        temp_max=entry["temp_max"],
                        temp_min=entry["temp_min"],
                    )
                )
    samples.extend(_jma_samples_for_date(jma_weathers, jma_pops, date))
    return samples


def collect_afternoon_samples(
    om_hourly: Dict[str, List[dict]],
    jma_weathers: List[Tuple[str, str]],
    jma_pops: List[Tuple[str, float]],
    now: dt.datetime,
) -> List[Sample]:
    date = now.date()
    samples = []
    for model, entries in om_hourly.items():
        temps, pops, categories = [], [], []
        for entry in entries:
            entry_dt = dt.datetime.fromisoformat(entry["time"]).replace(tzinfo=JST)
            if entry_dt.date() != date or entry_dt.hour < 12:
                continue
            if entry["temp"] is not None:
                temps.append(entry["temp"])
            if entry["pop"] is not None:
                pops.append(entry["pop"])
            if entry["category"]:
                categories.append(entry["category"])
        if not temps:
            continue
        top_category = Counter(categories).most_common(1)[0][0] if categories else None
        samples.append(
            Sample(
                source=f"open-meteo:{model}",
                category=top_category,
                pop=max(pops) if pops else None,
                temp_max=max(temps),
                temp_min=min(temps),
            )
        )

    for time_str, category in jma_weathers:
        if dt.datetime.fromisoformat(time_str).astimezone(JST).date() == date:
            samples.append(Sample(source="jma:weather", category=category))

    afternoon_pops = []
    for time_str, pop in jma_pops:
        t = dt.datetime.fromisoformat(time_str).astimezone(JST)
        if t.date() == date and t.hour >= 12:
            afternoon_pops.append(pop)
    if afternoon_pops:
        samples.append(Sample(source="jma:pop", pop=sum(afternoon_pops) / len(afternoon_pops)))

    return samples


def format_result(location_name: str, result: EnsembleResult) -> str:
    emoji = CATEGORY_EMOJI.get(result.category, "❔")
    confidence = CONFIDENCE_EMOJI.get(result.category_confidence, "")

    fields = [f"{emoji}{result.category}{confidence}"]
    if result.pop_avg is not None:
        fields.append(f"☔{result.pop_avg:.0f}%")
    if result.temp_max_avg is not None and result.temp_min_avg is not None:
        fields.append(f"🌡{result.temp_max_avg:.0f}/{result.temp_min_avg:.0f}℃")
    elif result.temp_max_avg is not None:
        fields.append(f"🌡{result.temp_max_avg:.0f}℃")

    return f"{location_name}  " + "  ".join(fields)


def overall_ntfy_tag(results: List[EnsembleResult]) -> str:
    categories = {r.category for r in results}
    for category in CATEGORY_ORDER:
        if category in categories:
            return CATEGORY_NTFY_TAG[category]
    return CATEGORY_NTFY_TAG["不明"]


def run(window: str, now: dt.datetime = None) -> Tuple[str, str]:
    now = now or dt.datetime.now(JST)
    lines = []
    results = []
    for location in config.LOCATIONS:
        raw = open_meteo.fetch(location.latitude, location.longitude)
        jma_data = jma.fetch_forecast(location.jma_office_code)
        jma_weathers = jma.extract_weathers(jma_data, location.jma_area_code)
        jma_pops = jma.extract_pops(jma_data, location.jma_area_code)

        if window == "afternoon":
            om_hourly = open_meteo.hourly_by_model(raw)
            samples = collect_afternoon_samples(om_hourly, jma_weathers, jma_pops, now)
        else:
            om_daily = open_meteo.daily_by_model(raw)
            samples = collect_daily_samples(window, om_daily, jma_weathers, jma_pops, now)

        result = summarize(samples)
        results.append(result)
        lines.append(format_result(location.name, result))

    message = "\n".join(lines)
    tag = overall_ntfy_tag(results)
    return message, tag


def main() -> None:
    parser = argparse.ArgumentParser(description="複数ソースの天気予報を集約してntfy.shへ通知する")
    parser.add_argument("--window", choices=config.WINDOWS, required=True)
    parser.add_argument("--dry-run", action="store_true", help="通知を送らず標準出力に表示する")
    args = parser.parse_args()

    title = WINDOW_TITLES[args.window]
    message, tag = run(args.window)

    if args.dry_run:
        print(f"[{title}] (tag={tag})\n{message}")
        return

    topic = os.environ["NTFY_TOPIC"]
    if not topic:
        raise SystemExit("NTFY_TOPIC is empty. Set it in the repository's Actions secrets.")
    # GitHub Actions passes an empty string (not "unset") for a secret that was
    # never configured, so os.environ.get's default never kicks in on its own.
    server = os.environ.get("NTFY_SERVER") or "https://ntfy.sh"
    send_ntfy(server, topic, title, message, tags=tag)


if __name__ == "__main__":
    main()
