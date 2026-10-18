"""cBioPortal public API client.

Thin transport: returns raw dictionaries and leaves parsing to the stage, so a
field rename upstream is a one-line fix in one place.

Two API quirks worth knowing, both verified against the live service:

* Mutations must be fetched by **POST** to ``/mutations/fetch``. The documented
  GET form returns HTTP 400 demanding an ``entrezGeneId``.
* ``GET /api/molecular-profiles?studyId=...`` silently ignores the filter and
  returns profiles for every study. Use the nested path under the study.
"""

from __future__ import annotations

from typing import Any

from neoag.io.http import CachedHTTP

BASE_URL = "https://www.cbioportal.org/api"
#: TCGA open-access data carry no publication restrictions; acknowledgement required.
CITATION = "cBioPortal (Cerami 2012; Gao 2013; de Bruijn 2023); data from the TCGA Research Network."


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class CBioPortalClient:
    def __init__(self, http: CachedHTTP, base_url: str = BASE_URL) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def study(self, study_id: str) -> dict[str, Any]:
        return self.http.get_json(f"{self.base_url}/studies/{study_id}")

    def sequenced_sample_ids(self, study_id: str) -> list[str]:
        """Sample IDs with mutation data.

        The per-study sample-list index omits ``sampleIds``, so the specific list
        must be fetched directly.
        """
        data = self.http.get_json(f"{self.base_url}/sample-lists/{study_id}_sequenced")
        return list(data.get("sampleIds", []))

    def mutations(self, study_id: str, sample_ids: list[str]) -> list[dict[str, Any]]:
        url = f"{self.base_url}/molecular-profiles/{study_id}_mutations/mutations/fetch"
        out: list[dict[str, Any]] = []
        for chunk in _chunks(sample_ids, 50):
            out.extend(
                self.http.post_json(url, {"sampleIds": chunk}, params={"projection": "DETAILED"})
            )
        return out

    def expression(
        self, study_id: str, sample_ids: list[str], entrez_gene_ids: list[int]
    ) -> list[dict[str, Any]]:
        """RSEM expression. Returns an empty list if the profile is unavailable."""
        if not entrez_gene_ids:
            return []
        url = f"{self.base_url}/molecular-profiles/{study_id}_rna_seq_v2_mrna/molecular-data/fetch"
        out: list[dict[str, Any]] = []
        for chunk in _chunks(sorted(set(entrez_gene_ids)), 500):
            out.extend(
                self.http.post_json(url, {"sampleIds": sample_ids, "entrezGeneIds": chunk})
            )
        return out
