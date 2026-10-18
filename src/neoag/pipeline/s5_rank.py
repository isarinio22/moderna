"""Stage 5 -- score, rank, and select the final epitopes.

Joins the predictions back onto the peptide pairs and picks the allele that
displays each mutant peptide best. The wild-type comparison is then read for
**that same allele**: comparing a mutant on one allele against its wild type on
a different one would measure the change of allele, not the effect of the
mutation.
"""

from __future__ import annotations

import time

import pandas as pd

from neoag.config import Settings, stage_fingerprint
from neoag.models import AnnotationSet, PeptidePair, RankingResult, ScoredEpitope
from neoag.pipeline.scoring import passes_gates, score_all
from neoag.pipeline.selection import select
from neoag.provenance import Provenance

STAGE = "s5_rank"


def expression_percentiles(annotation_set: AnnotationSet) -> dict[str, float | None]:
    """Rank each gene's expression within this tumour.

    RSEM values are not comparable between genes, so the useful question is not
    "how big is this number" but "how highly expressed is this gene compared with
    the others mutated in this tumour".
    """
    values = [
        (m.mutation_id, m.expression_rsem)
        for m in annotation_set.annotated
        if m.expression_rsem is not None
    ]
    if not values:
        return {m.mutation_id: None for m in annotation_set.annotated}
    ordered = sorted(values, key=lambda kv: (kv[1], kv[0]))
    n = len(ordered)
    ranks = {mid: (i + 1) / n for i, (mid, _) in enumerate(ordered)}
    return {m.mutation_id: ranks.get(m.mutation_id) for m in annotation_set.annotated}


def _lookup(frame: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Index predictions by (peptide, allele) for fast joining."""
    return {
        (row.peptide, row.allele): {
            "affinity": float(row.affinity),
            "presentation_score": float(row.presentation_score),
            "presentation_percentile": float(row.presentation_percentile),
        }
        for row in frame.itertuples(index=False)
    }


def run(
    settings: Settings,
    pairs: list[PeptidePair],
    predictions: pd.DataFrame,
    annotation_set: AnnotationSet,
    panel: str | None = None,
) -> RankingResult:
    """Execute stage 5 for one HLA panel."""
    started = time.monotonic()
    panel_name = panel or settings.hla.primary_panel
    alleles = settings.hla.panels[panel_name]
    index = _lookup(predictions)
    percentiles = expression_percentiles(annotation_set)

    scored: list[ScoredEpitope] = []
    gate_summary: dict[str, int] = {}

    for pair in pairs:
        # The allele that displays this mutant peptide best.
        best = None
        for allele in alleles:
            row = index.get((pair.mut_peptide, allele))
            if row is None:
                continue
            if best is None or row["presentation_score"] > best[1]["presentation_score"]:
                best = (allele, row)
        if best is None:
            continue
        allele, mut = best
        wt = index.get((pair.wt_peptide, allele))  # same allele, deliberately

        components, ratio = score_all(
            presentation_score=mut["presentation_score"],
            mut_affinity_nm=mut["affinity"],
            wt_affinity_nm=wt["affinity"] if wt else None,
            expression_percentile=percentiles.get(pair.mutation_id),
            peptide=pair.mut_peptide,
            cfg=settings.scoring,
        )
        ok, reason = passes_gates(
            mut["presentation_percentile"], mut["affinity"], settings.scoring.gates
        )
        if reason:
            gate_summary[reason] = gate_summary.get(reason, 0) + 1

        scored.append(
            ScoredEpitope(
                peptide_pair_id=pair.peptide_pair_id,
                mutation_id=pair.mutation_id,
                gene=pair.gene,
                mut_peptide=pair.mut_peptide,
                wt_peptide=pair.wt_peptide,
                length=pair.length,
                protein_position=pair.protein_position,
                mut_offset=pair.mut_offset,
                best_allele=allele,
                mut_affinity_nm=mut["affinity"],
                wt_affinity_nm=wt["affinity"] if wt else None,
                mut_presentation_score=mut["presentation_score"],
                mut_presentation_percentile=mut["presentation_percentile"],
                wt_presentation_score=wt["presentation_score"] if wt else None,
                agretopicity_ratio=ratio,
                expression_rsem=pair.expression_rsem,
                expression_percentile=percentiles.get(pair.mutation_id),
                components=components,
                rank=0,
                selected=False,
                exclusion_reason=None if ok else reason,
            )
        )

    final = select(scored, settings.selection)
    selected_ids = [e.peptide_pair_id for e in final if e.selected]

    return RankingResult(
        sample_id=annotation_set.sample_id,
        hla_alleles=list(alleles),
        epitopes=final,
        selected_ids=selected_ids,
        weights=dict(settings.scoring.weights),
        gate_summary=gate_summary,
        provenance=Provenance(
            stage=STAGE,
            origin=annotation_set.provenance.origin,
            created_utc=Provenance.now_utc(),
            config_fingerprint=stage_fingerprint(settings, STAGE),
            wall_seconds=round(time.monotonic() - started, 3),
            counts={
                "candidates": len(final),
                "selected": len(selected_ids),
                "gated_out": sum(gate_summary.values()),
            },
            notes=[f"hla_panel={panel_name}", settings.hla.assumption_note],
        ),
    )
