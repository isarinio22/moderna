"""Ensembl GRCh37 REST client -- fallback protein sequences only.

Deliberately pinned to the GRCh37 service. The current Ensembl REST host is on
the forbidden list in :mod:`neoag.io.http`, so an accidental switch raises rather
than quietly returning a protein with different numbering.
"""

from __future__ import annotations

from neoag.io.http import CachedHTTP

BASE_URL = "https://grch37.rest.ensembl.org"


class Ensembl37Client:
    def __init__(self, http: CachedHTTP, base_url: str = BASE_URL) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def protein_sequence(self, transcript_id: str) -> str | None:
        """Protein sequence for a transcript, or ``None`` if unavailable."""
        try:
            data = self.http.get_json(
                f"{self.base_url}/sequence/id/{transcript_id}",
                params={"type": "protein", "content-type": "application/json"},
            )
        except Exception:  # noqa: BLE001 - fallback source; absence is recorded upstream
            return None
        seq = data.get("seq") if isinstance(data, dict) else None
        return seq.rstrip("*") if seq else None

    def url_for(self, transcript_id: str) -> str:
        return f"{self.base_url}/sequence/id/{transcript_id}?type=protein"
