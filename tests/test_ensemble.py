from weather_notify.ensemble import Sample, confidence_label, summarize


def test_summarize_majority_category():
    samples = [
        Sample("a", category="晴れ"),
        Sample("b", category="晴れ"),
        Sample("c", category="くもり"),
    ]
    result = summarize(samples)
    assert result.category == "晴れ"
    assert result.category_votes == {"晴れ": 2, "くもり": 1}


def test_summarize_full_agreement_is_high_confidence():
    samples = [Sample("a", category="雨"), Sample("b", category="雨")]
    result = summarize(samples)
    assert result.category_confidence == "高"


def test_summarize_three_way_split_is_low_confidence():
    samples = [Sample("a", category="雨"), Sample("b", category="晴れ"), Sample("c", category="くもり")]
    result = summarize(samples)
    assert result.category_confidence == "低"


def test_summarize_even_split_is_medium_confidence():
    samples = [Sample("a", category="雨"), Sample("b", category="晴れ")]
    result = summarize(samples)
    assert result.category_confidence == "中"


def test_summarize_pop_and_temp_averages():
    samples = [
        Sample("a", pop=30, temp_max=28.0, temp_min=20.0),
        Sample("b", pop=50, temp_max=30.0, temp_min=22.0),
    ]
    result = summarize(samples)
    assert result.pop_avg == 40
    assert result.pop_range == (30, 50)
    assert result.temp_max_avg == 29.0
    assert result.temp_max_range == (28.0, 30.0)
    assert result.temp_min_avg == 21.0


def test_summarize_ignores_unknown_category():
    samples = [Sample("a", category="不明"), Sample("b", category="晴れ")]
    result = summarize(samples)
    assert result.category == "晴れ"
    assert result.category_confidence == "高"


def test_summarize_no_samples_returns_unknown():
    result = summarize([])
    assert result.category == "不明"
    assert result.category_confidence == "低"
    assert result.pop_avg is None


def test_confidence_label_thresholds():
    assert confidence_label(1.0) == "高"
    assert confidence_label(0.8) == "高"
    assert confidence_label(0.6) == "中"
    assert confidence_label(0.5) == "中"
    assert confidence_label(0.2) == "低"
