"""Stage 4 -- predict MHC class I presentation.

The expensive stage, so it is arranged to do the least work that is still
correct:

* Peptides are deduplicated across the whole sample before prediction. The same
  sequence often arises from several windows, and predicting it once is enough.
* Prediction runs over the **union of every HLA panel**, not just the primary
  one. The models are the slow part and running them once lets the website show
  how the selection changes with HLA type for free.
* Results are cached as Parquet, so re-ranking with different weights costs
  seconds instead of minutes.
"""

from __future__ import annotations

import time

import pandas as pd

from neoag.config import Settings, stage_fingerprint
from neoag.models import PeptidePair
from neoag.pipeline.predictors.base import PresentationPredictor
from neoag.provenance import Provenance

STAGE = "s4_predict"


def unique_peptides(pairs: list[PeptidePair]) -> list[str]:
    """Every distinct sequence needing a prediction, mutant and wild-type alike."""
    peptides: set[str] = set()
    for pair in pairs:
        peptides.add(pair.mut_peptide)
        peptides.add(pair.wt_peptide)
    return sorted(peptides)


def run(
    settings: Settings, pairs: list[PeptidePair], predictor: PresentationPredictor
) -> tuple[pd.DataFrame, Provenance]:
    """Execute stage 4."""
    started = time.monotonic()
    peptides = unique_peptides(pairs)
    alleles = settings.hla.all_alleles

    frame = predictor.predict(peptides, alleles)
    frame = frame.sort_values(["peptide", "allele"], kind="stable").reset_index(drop=True)

    provenance = Provenance(
        stage=STAGE,
        origin="cbioportal" if not settings.source.use_synthetic else "synthetic",
        created_utc=Provenance.now_utc(),
        config_fingerprint=stage_fingerprint(settings, STAGE),
        wall_seconds=round(time.monotonic() - started, 3),
        counts={
            "pairs": len(pairs),
            "unique_peptides": len(peptides),
            "alleles": len(alleles),
            "predictions": len(frame),
        },
        notes=[f"predictor={getattr(predictor, 'name', 'unknown')}"]
        + (
            []
            if getattr(predictor, "is_real_prediction", True)
            else ["PLACEHOLDER SCORES: the stub predictor has no biological meaning."]
        ),
    )
    return frame, provenance
