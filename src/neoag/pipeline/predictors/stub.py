"""A deterministic predictor that needs no model.

Scores are derived from a hash of the peptide and allele, so they are stable
across runs and machines while being spread over plausible ranges. They carry no
biological meaning whatsoever.

This exists so the pipeline's structure can be tested and demonstrated
independently of the model: CI runs every stage in seconds, and the output is
labelled so it can never be mistaken for a real prediction.
"""

from __future__ import annotations

import pandas as pd

from neoag.pipeline.predictors.base import PREDICTION_COLUMNS, PredictionFrame
from neoag.util.hashing import unit_interval

WARNING = (
    "StubPredictor scores are hash-derived placeholders with no biological meaning. "
    "Use the mhcflurry predictor for any result that is meant to mean anything."
)


class StubPredictor:
    """Hash-based stand-in for a presentation predictor."""

    name = "stub-1"
    is_real_prediction = False

    def predict(self, peptides: list[str], alleles: list[str]) -> PredictionFrame:
        rows = []
        for peptide in peptides:
            for allele in alleles:
                u = unit_interval(peptide, allele)
                v = unit_interval(allele, peptide)
                rows.append(
                    {
                        "peptide": peptide,
                        "allele": allele,
                        # Log-uniform over roughly 1 nM .. 50 uM, like real affinities.
                        "affinity": round(10 ** (0 + 4.7 * u), 4),
                        "affinity_percentile": round(100.0 * u, 4),
                        "processing_score": round(v, 6),
                        "presentation_score": round(1.0 - u, 6),
                        "presentation_percentile": round(100.0 * u, 4),
                    }
                )
        return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
