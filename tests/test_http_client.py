import requests

from weather_notify.http_client import get_json


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_get_json_returns_payload_on_first_success(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("weather_notify.http_client.requests.get", fake_get)

    assert get_json("https://example.test") == {"ok": True}
    assert len(calls) == 1


def test_get_json_retries_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_get(url, params=None, timeout=None):
        calls["count"] += 1
        if calls["count"] < 3:
            raise requests.exceptions.ReadTimeout("timed out")
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("weather_notify.http_client.requests.get", fake_get)
    monkeypatch.setattr("weather_notify.http_client.time.sleep", lambda s: None)

    assert get_json("https://example.test", retries=3) == {"ok": True}
    assert calls["count"] == 3


def test_get_json_raises_last_error_after_exhausting_retries(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr("weather_notify.http_client.requests.get", fake_get)
    monkeypatch.setattr("weather_notify.http_client.time.sleep", lambda s: None)

    try:
        get_json("https://example.test", retries=2)
        assert False, "expected ReadTimeout to propagate"
    except requests.exceptions.ReadTimeout:
        pass
