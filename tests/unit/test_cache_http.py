"""HTTP caching, offline mode and retry behaviour."""

from __future__ import annotations

import pytest
import requests

from neoag.errors import ApiClientError, CacheMissError
from neoag.io.cache import CachedResponse, CacheKey, HttpCache
from neoag.io.http import CachedHTTP


class FakeResponse:
    def __init__(self, status, payload=None, headers=None, text=""):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.headers = {}

    def request(self, *args, **kwargs):
        self.calls += 1
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def cache(tmp_path):
    return HttpCache(tmp_path / "http")


class TestCacheKey:
    def test_list_order_does_not_fork_the_cache(self):
        a = CacheKey("POST", "u", None, {"sampleIds": ["B", "A"]})
        b = CacheKey("POST", "u", None, {"sampleIds": ["A", "B"]})
        assert a.digest() == b.digest()

    def test_dict_key_order_does_not_matter(self):
        a = CacheKey("POST", "u", None, {"x": 1, "y": 2})
        b = CacheKey("POST", "u", None, {"y": 2, "x": 1})
        assert a.digest() == b.digest()

    def test_different_bodies_differ(self):
        a = CacheKey("POST", "u", None, {"sampleIds": ["A"]})
        b = CacheKey("POST", "u", None, {"sampleIds": ["C"]})
        assert a.digest() != b.digest()

    def test_method_and_url_matter(self):
        assert CacheKey("GET", "u").digest() != CacheKey("POST", "u").digest()
        assert CacheKey("GET", "u").digest() != CacheKey("GET", "v").digest()


class TestOfflineMode:
    def test_cache_miss_raises_without_touching_the_network(self, cache):
        session = FakeSession([])
        http = CachedHTTP(cache, "offline", session=session)
        with pytest.raises(CacheMissError, match="offline mode"):
            http.get_json("https://example.org/x")
        assert session.calls == 0

    def test_cache_hit_is_served_offline(self, cache):
        key = CacheKey("GET", "https://example.org/x", None, None)
        cache.put(key, CachedResponse(200, "https://example.org/x", {"ok": True}, "now"))
        http = CachedHTTP(cache, "offline", session=FakeSession([]))
        assert http.get_json("https://example.org/x") == {"ok": True}

    def test_refresh_mode_bypasses_the_cache(self, cache):
        key = CacheKey("GET", "https://example.org/x", None, None)
        cache.put(key, CachedResponse(200, "x", {"stale": True}, "now"))
        session = FakeSession([FakeResponse(200, {"fresh": True})])
        http = CachedHTTP(cache, "refresh", session=session, sleep=lambda s: None)
        assert http.get_json("https://example.org/x") == {"fresh": True}


class TestRetries:
    def test_retry_after_header_is_honoured(self, cache):
        slept = []
        session = FakeSession(
            [FakeResponse(429, headers={"Retry-After": "2"}), FakeResponse(200, {"ok": 1})]
        )
        http = CachedHTTP(cache, "auto", session=session, sleep=slept.append)
        assert http.get_json("https://example.org/x") == {"ok": 1}
        assert slept == [2.0]

    def test_retry_after_is_capped(self, cache):
        slept = []
        session = FakeSession(
            [FakeResponse(503, headers={"Retry-After": "9999"}), FakeResponse(200, {"ok": 1})]
        )
        http = CachedHTTP(cache, "auto", session=session, sleep=slept.append, max_backoff=30)
        http.get_json("https://example.org/x")
        assert slept == [30.0]

    def test_server_error_then_success(self, cache):
        session = FakeSession([FakeResponse(500), FakeResponse(502), FakeResponse(200, {"ok": 1})])
        http = CachedHTTP(cache, "auto", session=session, sleep=lambda s: None)
        assert http.get_json("https://example.org/x") == {"ok": 1}
        assert session.calls == 3

    def test_client_error_is_not_retried(self, cache):
        session = FakeSession([FakeResponse(404, text="nope")])
        http = CachedHTTP(cache, "auto", session=session, sleep=lambda s: None)
        with pytest.raises(ApiClientError, match="404"):
            http.get_json("https://example.org/x")
        assert session.calls == 1

    def test_connection_errors_are_retried(self, cache):
        session = FakeSession([requests.ConnectionError("down"), FakeResponse(200, {"ok": 1})])
        http = CachedHTTP(cache, "auto", session=session, sleep=lambda s: None)
        assert http.get_json("https://example.org/x") == {"ok": 1}

    def test_gives_up_after_max_retries(self, cache):
        session = FakeSession([FakeResponse(503)] * 5)
        http = CachedHTTP(cache, "auto", session=session, sleep=lambda s: None, max_retries=5)
        with pytest.raises(ApiClientError, match="giving up"):
            http.get_json("https://example.org/x")


def test_only_successful_responses_are_cached(cache):
    session = FakeSession([FakeResponse(500), FakeResponse(200, {"ok": 1})])
    http = CachedHTTP(cache, "auto", session=session, sleep=lambda s: None)
    http.get_json("https://example.org/x")
    offline = CachedHTTP(cache, "offline", session=FakeSession([]))
    assert offline.get_json("https://example.org/x") == {"ok": 1}


def test_cache_seeding_populates_from_committed_responses(tmp_path):
    seed = tmp_path / "seed"
    (seed / "ab").mkdir(parents=True)
    source = HttpCache(seed)
    key = CacheKey("GET", "https://example.org/x", None, None)
    source.put(key, CachedResponse(200, "x", {"seeded": True}, "now"))

    target = HttpCache(tmp_path / "live")
    assert target.seed_from(seed) >= 1
    assert target.get(key).body == {"seeded": True}
