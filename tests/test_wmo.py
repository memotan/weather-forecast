from weather_notify.wmo import jma_text_to_category, wmo_code_to_category


def test_wmo_code_to_category_clear():
    assert wmo_code_to_category(0) == "晴れ"


def test_wmo_code_to_category_cloudy():
    assert wmo_code_to_category(3) == "くもり"


def test_wmo_code_to_category_rain():
    assert wmo_code_to_category(61) == "雨"


def test_wmo_code_to_category_thunderstorm():
    assert wmo_code_to_category(95) == "雷雨"


def test_wmo_code_to_category_unknown_when_missing():
    assert wmo_code_to_category(None) == "不明"


def test_jma_text_to_category_prioritizes_rain_over_clear():
    assert jma_text_to_category("晴れ時々雨") == "雨"


def test_jma_text_to_category_cloudy():
    assert jma_text_to_category("晴れ時々曇り") == "くもり"


def test_jma_text_to_category_clear():
    assert jma_text_to_category("晴れ") == "晴れ"


def test_jma_text_to_category_empty():
    assert jma_text_to_category("") == "不明"
