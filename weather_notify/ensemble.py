from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Sample:
    source: str
    category: Optional[str] = None
    pop: Optional[float] = None  # precipitation probability, 0-100
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None


@dataclass
class EnsembleResult:
    category: str
    category_confidence: str
    category_votes: Dict[str, int]
    pop_avg: Optional[float]
    pop_range: Optional[Tuple[float, float]]
    temp_max_avg: Optional[float]
    temp_max_range: Optional[Tuple[float, float]]
    temp_min_avg: Optional[float]
    temp_min_range: Optional[Tuple[float, float]]
    sample_count: int


def confidence_label(agreement_ratio: float) -> str:
    if agreement_ratio >= 0.8:
        return "高"
    if agreement_ratio >= 0.5:
        return "中"
    return "低"


def _avg_and_range(values: List[float], ndigits: int = 0):
    if not values:
        return None, None
    avg = round(sum(values) / len(values), ndigits)
    rng = (round(min(values), ndigits), round(max(values), ndigits))
    return avg, rng


def summarize(samples: List[Sample]) -> EnsembleResult:
    categories = [s.category for s in samples if s.category and s.category != "不明"]
    votes = Counter(categories)
    if votes:
        top_category, top_count = votes.most_common(1)[0]
        agreement_ratio = top_count / len(categories)
    else:
        top_category, agreement_ratio = "不明", 0.0

    pops = [s.pop for s in samples if s.pop is not None]
    tmax = [s.temp_max for s in samples if s.temp_max is not None]
    tmin = [s.temp_min for s in samples if s.temp_min is not None]

    pop_avg, pop_range = _avg_and_range(pops, ndigits=0)
    temp_max_avg, temp_max_range = _avg_and_range(tmax, ndigits=1)
    temp_min_avg, temp_min_range = _avg_and_range(tmin, ndigits=1)

    return EnsembleResult(
        category=top_category,
        category_confidence=confidence_label(agreement_ratio),
        category_votes=dict(votes),
        pop_avg=pop_avg,
        pop_range=pop_range,
        temp_max_avg=temp_max_avg,
        temp_max_range=temp_max_range,
        temp_min_avg=temp_min_avg,
        temp_min_range=temp_min_range,
        sample_count=len(samples),
    )
