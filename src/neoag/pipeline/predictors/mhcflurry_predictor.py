"""MHCflurry presentation predictor.

MHCflurry 2.3 is PyTorch-based and Apache-2.0 licensed. Its models are trained on
IEDB binding data and published mass-spectrometry ligand datasets
(O'Donnell et al., *Cell Systems*, 2020).

Each allele is submitted as its own sample. That is what makes the mutant and
wild-type peptides comparable: both are scored against the *same* allele, so the
difference between them reflects the mutation rather than a change of allele.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from neoag.errors import PredictorUnavailableError
from neoag.pipeline.predictors.base import PREDICTION_COLUMNS, PredictionFrame

FETCH_HINT = "mhcflurry downloads fetch models_class1_presentation"


class MHCflurryPredictor:
    """Thin wrapper around ``Class1PresentationPredictor``."""

    name = "mhcflurry-2.3"
    is_real_prediction = True

    def __init__(self, cache_dir: Path | None = None) -> None:
        # MHCflurry reads this at import time, so it must be set first.
        if cache_dir is not None:
            os.environ.setdefault("MHCFLURRY_DOWNLOADS_DIR", str(cache_dir))
        try:
            from mhcflurry import Class1PresentationPredictor
        except ImportError as exc:
            raise PredictorUnavailableError(
                "mhcflurry is not installed. Install it with "
                "`pip install -e '.[predict]'`, or run with predictor: stub."
            ) from exc
        try:
            self._predictor = Class1PresentationPredictor.load()
        except Exception as exc:
            raise PredictorUnavailableError(
                f"could not load MHCflurry models ({exc}). Download them with:\n  {FETCH_HINT}"
            ) from exc
        import mhcflurry

        self.name = f"mhcflurry-{mhcflurry.__version__}"

    def predict(self, peptides: list[str], alleles: list[str]) -> PredictionFrame:
        if not peptides or not alleles:
            return pd.DataFrame(columns=PREDICTION_COLUMNS)
        # One allele per "sample": keeps mutant and wild-type on the same allele.
        result = self._predictor.predict(
            peptides=list(peptides),
            alleles={allele: [allele] for allele in alleles},
            include_affinity_percentile=True,
            verbose=0,
        )
        frame = result.rename(columns={"sample_name": "allele", "best_allele": "_best"})
        for column in PREDICTION_COLUMNS:
            if column not in frame.columns:
                frame[column] = float("nan")
        return frame[PREDICTION_COLUMNS].reset_index(drop=True)
