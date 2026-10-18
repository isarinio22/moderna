"""MHCflurry behaviour, where the models are available.

Marked ``models`` and deselected by default, since the download is ~160 MB.
"""

from __future__ import annotations

import pytest

from neoag.paths import Paths
from neoag.pipeline.predictors.base import PREDICTION_COLUMNS, load_predictor

pytestmark = pytest.mark.models


@pytest.fixture(scope="module")
def predictor():
    try:
        return load_predictor("mhcflurry", Paths().mhcflurry_cache)
    except Exception as exc:
        pytest.skip(f"MHCflurry models unavailable: {exc}")


def test_returns_every_column_the_pipeline_reads(predictor):
    frame = predictor.predict(["SIINFEKL"], ["HLA-A*02:01"])
    assert set(PREDICTION_COLUMNS) <= set(frame.columns)


def test_known_a0201_epitopes_are_strong_binders(predictor):
    """GILGFVFTL (influenza M1) and NLVPMVATV (CMV pp65) are textbook A*02:01 epitopes."""
    frame = predictor.predict(["GILGFVFTL", "NLVPMVATV"], ["HLA-A*02:01"])
    assert (frame["presentation_percentile"] < 2.0).all()
    assert (frame["affinity"] < 500).all()


def test_allele_specificity_is_reflected(predictor):
    """An A*02:01 epitope should not look equally good on B*07:02."""
    frame = predictor.predict(["GILGFVFTL"], ["HLA-A*02:01", "HLA-B*07:02"])
    by_allele = frame.set_index("allele")["presentation_score"]
    assert by_allele["HLA-A*02:01"] > by_allele["HLA-B*07:02"]


def test_one_row_per_peptide_allele_pair(predictor):
    frame = predictor.predict(["SIINFEKL", "GILGFVFTL"], ["HLA-A*02:01", "HLA-B*07:02"])
    assert len(frame) == 4
