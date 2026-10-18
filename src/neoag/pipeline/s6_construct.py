"""Stage 6 -- assemble the conceptual mRNA construct.

The output is a teaching illustration: it shows how selected epitopes would be
arranged into a single message, with every region labelled. It is not a
manufacturable sequence and is marked as conceptual in the data model, in the
JSON, and in the FASTA header.
"""

from __future__ import annotations

import time

from neoag.config import Settings, stage_fingerprint
from neoag.models import MRNAConstruct, RankingResult
from neoag.pipeline.construct.assemble import MODIFIED_BASE_NOTE, assemble, summarize
from neoag.pipeline.construct.junctions import order_epitopes, screen_junctions
from neoag.pipeline.predictors.base import PresentationPredictor
from neoag.provenance import Provenance

STAGE = "s6_construct"


def run(
    settings: Settings, ranking: RankingResult, predictor: PresentationPredictor
) -> MRNAConstruct:
    """Execute stage 6."""
    started = time.monotonic()
    selected = [e for e in ranking.epitopes if e.selected]
    if not selected:
        raise ValueError(
            "no epitopes were selected, so there is nothing to assemble. "
            "Check the scoring gates in config -- they may be too strict for this sample."
        )

    by_id = {e.peptide_pair_id: e for e in selected}
    cfg = settings.mrna

    order = order_epitopes(
        selected, cfg.linker, cfg.junction_screen_lengths, ranking.hla_alleles,
        predictor, cfg.junction_ordering,
    )
    junctions = screen_junctions(
        order, by_id, cfg.linker, cfg.junction_screen_lengths, ranking.hla_alleles, predictor
    )
    full, blocks, cds_aa, optimizer, constraints = assemble(
        order, by_id, cfg, settings.run.seed, junctions
    )
    stats = summarize(full, cds_aa)

    return MRNAConstruct(
        disclaimer=" ".join(cfg.disclaimer.split()),
        sample_id=ranking.sample_id,
        epitope_order=order,
        cds_aa=cds_aa,
        full_sequence=full,
        blocks=blocks,
        gc_content=float(stats["gc_content"]),
        cds_length_nt=int(stats["cds_length_nt"]),
        total_length_nt=int(stats["total_length_nt"]),
        codon_optimizer=optimizer,  # type: ignore[arg-type]
        constraints_satisfied=constraints,
        junction_report=junctions,
        provenance=Provenance(
            stage=STAGE,
            origin=ranking.provenance.origin,
            created_utc=Provenance.now_utc(),
            config_fingerprint=stage_fingerprint(settings, STAGE),
            wall_seconds=round(time.monotonic() - started, 3),
            counts={
                "epitopes": len(order),
                "junctions": len(junctions),
                "junctions_with_strong": sum(1 for j in junctions if j.n_strong_binders),
                "total_length_nt": int(stats["total_length_nt"]),
            },
            notes=[
                MODIFIED_BASE_NOTE,
                "CONCEPTUAL CONSTRUCT -- not manufacturable, not validated.",
            ],
        ),
    )
