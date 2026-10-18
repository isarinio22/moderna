"""Genome Nexus annotation client.

cBioPortal gives a gene symbol and a protein change but no transcript or UniProt
accession, and the protein sequence has to come from somewhere. Genome Nexus is
the annotator cBioPortal itself uses, it is free and needs no key, and its
default build is GRCh37 -- which matches the TCGA data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neoag.io.http import CachedHTTP

BASE_URL = "https://www.genomenexus.org"


@dataclass(frozen=True)
class TranscriptPick:
    """The transcript consequence chosen for one variant."""

    transcript_id: str | None
    uniprot_acc: str | None
    hgvsp_short: str | None
    aa_ref: str | None
    aa_alt: str | None
    protein_position: int | None


class GenomeNexusClient:
    def __init__(self, http: CachedHTTP, base_url: str = BASE_URL) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def annotate(self, hgvs_g: list[str]) -> dict[str, dict[str, Any]]:
        """Annotate variants in batches. Returns a mapping keyed by HGVS-g string."""
        out: dict[str, dict[str, Any]] = {}
        unique = sorted(set(hgvs_g))
        for i in range(0, len(unique), 100):
            chunk = unique[i : i + 100]
            response = self.http.post_json(
                f"{self.base_url}/annotation", chunk, params={"fields": "annotation_summary"}
            )
            for record in response:
                key = record.get("variant") or record.get("originalVariantQuery")
                if key:
                    out[key] = record
        return out


def _parse_protein_position(value: Any) -> int | None:
    """Protein position arrives as an int, or as a ``start/end`` string."""
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return _parse_protein_position(value.get("start"))
    if isinstance(value, str):
        head = value.split("/")[0].strip()
        if head.isdigit():
            return int(head)
    return None


def pick_transcript(record: dict[str, Any], expected_aa: str, expected_pos: int) -> TranscriptPick:
    """Choose a transcript consequence, preferring one that agrees with the variant call.

    The canonical transcript is tried first. If its reference amino acid or
    position disagrees with what cBioPortal reported, the other consequences are
    scanned for one that agrees before giving up -- a disagreement usually means
    the canonical transcript is simply a different isoform, not that the variant
    is wrong.
    """
    summary = (record.get("annotation_summary") or {})
    candidates: list[dict[str, Any]] = []
    canonical = summary.get("transcriptConsequenceSummary")
    if canonical:
        candidates.append(canonical)
    candidates.extend(summary.get("transcriptConsequenceSummaries") or [])

    fallback: TranscriptPick | None = None
    for cand in candidates:
        pick = TranscriptPick(
            transcript_id=cand.get("transcriptId") or None,
            uniprot_acc=cand.get("uniprotId") or None,
            hgvsp_short=cand.get("hgvspShort") or None,
            aa_ref=cand.get("aminoAcidRef") or None,
            aa_alt=cand.get("aminoAcidAlt") or None,
            protein_position=_parse_protein_position(cand.get("proteinPosition")),
        )
        if pick.aa_ref == expected_aa and pick.protein_position == expected_pos:
            return pick
        if fallback is None and pick.uniprot_acc:
            fallback = pick
    return fallback or TranscriptPick(None, None, None, None, None, None)
