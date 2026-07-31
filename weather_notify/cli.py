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

JST = ZoneInfo("Asia/Tokyo")

WINDOW_TITLES = {
    "morning": "本日の天気予報",
    "afternoon": "本日午後〜夜の天気予報",
    "evening": "明日の天気予報",
}


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
    lines = [f"■ {location_name}"]
    if result.category_votes:
        votes_str = "・".join(
            f"{k}:{v}" for k, v in sorted(result.category_votes.items(), key=lambda kv: -kv[1])
        )
        lines.append(f"天気: {result.category}（確度:{result.category_confidence} / {votes_str}）")
    else:
        lines.append("天気: 不明")

    if result.pop_avg is not None:
        rng = f"（{result.pop_range[0]:.0f}〜{result.pop_range[1]:.0f}%）" if result.pop_range else ""
        lines.append(f"降水確率: 平均{result.pop_avg:.0f}%{rng}")

    if result.temp_max_avg is not None:
        rng = f"（{result.temp_max_range[0]}〜{result.temp_max_range[1]}℃）" if result.temp_max_range else ""
        lines.append(f"最高気温: 平均{result.temp_max_avg}℃{rng}")

    if result.temp_min_avg is not None:
        rng = f"（{result.temp_min_range[0]}〜{result.temp_min_range[1]}℃）" if result.temp_min_range else ""
        lines.append(f"最低気温: 平均{result.temp_min_avg}℃{rng}")

    lines.append(f"(情報源 {result.sample_count}件)")
    return "\n".join(lines)


def run(window: str, now: dt.datetime = None) -> str:
    now = now or dt.datetime.now(JST)
    blocks = []
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
        blocks.append(format_result(location.name, result))

    return "\n\n".join(blocks)


def main() -> None:
    parser = argparse.ArgumentParser(description="複数ソースの天気予報を集約してntfy.shへ通知する")
    parser.add_argument("--window", choices=config.WINDOWS, required=True)
    parser.add_argument("--dry-run", action="store_true", help="通知を送らず標準出力に表示する")
    args = parser.parse_args()

    title = WINDOW_TITLES[args.window]
    message = run(args.window)

    if args.dry_run:
        print(f"[{title}]\n{message}")
        return

    topic = os.environ["NTFY_TOPIC"]
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
    send_ntfy(server, topic, title, message)


if __name__ == "__main__":
    main()
