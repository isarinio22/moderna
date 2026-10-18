"""Cached HTTP with retries, backoff, and a hard block on the wrong genome build.

The forbidden-host list is the important part. TCGA variant calls use GRCh37
protein numbering. The current (GRCh38) Ensembl REST service returns a different,
longer protein model for some genes -- BRAF is 806 residues there with threonine
at position 600, against 766 residues with valine in GRCh37. Resolving a
transcript against the wrong service yields peptides that look entirely plausible
and are wrong, with no error raised anywhere.

That class of bug cannot be caught by review, so it is blocked at the transport
layer: the wrong host raises before a request is made.
"""

from __future__ import annotations

import datetime as _dt
import random
import time
from typing import Any
from urllib.parse import urlparse

import requests

from neoag.errors import ApiClientError, CacheMissError, ForbiddenHostError
from neoag.io.cache import CachedResponse, CacheKey, HttpCache

#: Hosts this package refuses to contact, with the reason.
FORBIDDEN_HOSTS: dict[str, str] = {
    "rest.ensembl.org": (
        "GRCh38 endpoint. TCGA data is GRCh37 and protein numbering differs "
        "(e.g. BRAF is 806 aa with T600 here vs 766 aa with V600 in GRCh37). "
        "Use grch37.rest.ensembl.org."
    )
}

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def check_host(url: str) -> None:
    """Raise if the URL targets a host that would corrupt results."""
    host = (urlparse(url).hostname or "").lower()
    if host in FORBIDDEN_HOSTS:
        raise ForbiddenHostError(f"refusing to contact {host}: {FORBIDDEN_HOSTS[host]}")


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        when = _dt.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=_dt.UTC)
    except ValueError:
        return None
    return max(0.0, (when - _dt.datetime.now(_dt.UTC)).total_seconds())


class CachedHTTP:
    """A small JSON HTTP client: cache first, then network, with polite retries."""

    def __init__(
        self,
        cache: HttpCache,
        mode: str = "auto",
        *,
        user_agent: str = "neoag-educational/0.1 (github.com/isarinio22/moderna)",
        timeout: float = 30.0,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        max_backoff: float = 60.0,
        seed: int = 1337,
        sleep: Any = time.sleep,
        session: requests.Session | None = None,
    ) -> None:
        self.cache = cache
        self.mode = mode
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.max_backoff = max_backoff
        self._rng = random.Random(seed)
        self._sleep = sleep
        self._session = session or requests.Session()
        self._session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        self.stats = {"hits": 0, "misses": 0, "retries": 0}

    # -- public ------------------------------------------------------------
    def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        return self._request("GET", url, params=params)

    def post_json(self, url: str, body: Any, params: dict[str, str] | None = None) -> Any:
        return self._request("POST", url, params=params, body=body)

    def get_text(self, url: str, params: dict[str, str] | None = None) -> str:
        return self._request("GET", url, params=params, as_text=True)

    # -- internals ---------------------------------------------------------
    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        body: Any = None,
        as_text: bool = False,
    ) -> Any:
        check_host(url)
        key = CacheKey(method=method, url=url, params=params, body=body)

        if self.mode != "refresh":
            cached = self.cache.get(key)
            if cached is not None:
                self.stats["hits"] += 1
                return cached.body

        if self.mode == "offline":
            raise CacheMissError(
                f"offline mode: no cached response for {method} {url}. "
                "Run once with network access, or use config/synthetic.yaml."
            )

        self.stats["misses"] += 1
        payload = self._fetch(method, url, params=params, body=body, as_text=as_text)
        fetched = _dt.datetime.now(_dt.UTC).isoformat()
        self.cache.put(key, CachedResponse(200, url, payload, fetched))
        return payload

    def _fetch(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None,
        body: Any,
        as_text: bool,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._session.request(
                    method, url, params=params, json=body, timeout=self.timeout
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                self._backoff(attempt, None)
                continue

            if response.status_code == 200:
                return response.text if as_text else response.json()

            if response.status_code in RETRY_STATUSES:
                last_error = ApiClientError(f"{response.status_code} from {url}")
                self._backoff(attempt, _retry_after_seconds(response.headers.get("Retry-After")))
                continue

            raise ApiClientError(
                f"{response.status_code} from {url}: {response.text[:400]}"
            )

        raise ApiClientError(
            f"giving up on {method} {url} after {self.max_retries} attempts"
        ) from last_error

    def _backoff(self, attempt: int, retry_after: float | None) -> None:
        self.stats["retries"] += 1
        if retry_after is not None:
            delay = min(retry_after, self.max_backoff)
        else:
            delay = min(self.max_backoff, self.backoff_base * (2**attempt))
            delay += self._rng.uniform(0, delay * 0.1)
        self._sleep(delay)
