"""Predictor interface.

Behind a protocol so the whole pipeline can run end-to-end without the 160 MB
model download -- which is what lets CI, and anyone cloning the repo, see the
real data flow in seconds instead of waiting on a download they may not want.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

import pandas as pd

from neoag.errors import PredictorUnavailableError

#: Columns every predictor must return.
PREDICTION_COLUMNS = [
    "peptide",
    "allele",
    "affinity",
    "affinity_percentile",
    "processing_score",
    "presentation_score",
    "presentation_percentile",
]

PredictionFrame = pd.DataFrame


@runtime_checkable
class PresentationPredictor(Protocol):
    """Predicts how likely a peptide is to be displayed by a given HLA allele."""

    name: str

    def predict(self, peptides: list[str], alleles: list[str]) -> PredictionFrame:
        """Return one row per (peptide, allele) with :data:`PREDICTION_COLUMNS`."""
        ...


def load_predictor(
    kind: Literal["mhcflurry", "stub"], cache_dir: Path | None = None
) -> PresentationPredictor:
    """Construct a predictor by name."""
    if kind == "stub":
        from neoag.pipeline.predictors.stub import StubPredictor

        return StubPredictor()
    if kind == "mhcflurry":
        from neoag.pipeline.predictors.mhcflurry_predictor import MHCflurryPredictor

        return MHCflurryPredictor(cache_dir)
    raise PredictorUnavailableError(f"unknown predictor {kind!r}")
