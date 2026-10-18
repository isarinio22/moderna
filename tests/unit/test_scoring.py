"""Scoring components and gates."""

from __future__ import annotations

import pytest

from neoag.config import AgretopicityCfg, ExpressionCfg, GatesCfg, QualityCfg, ScoringCfg
from neoag.pipeline.scoring import (
    agretopicity_component,
    combine,
    expression_component,
    passes_gates,
    presentation_component,
    quality_component,
)


class TestAgretopicity:
    """How much better the mutant binds than the wild type.

    Lower nM means tighter binding, so ratio = wt_nM / mut_nM above 1 means the
    mutation improved binding -- which is what makes a fragment newly visible.
    """

    def test_mutant_much_tighter_scores_maximum(self):
        score, ratio = agretopicity_component(50.0, 5000.0, AgretopicityCfg())
        assert score == 1.0
        assert ratio == 100.0

    def test_mutant_much_weaker_scores_zero(self):
        score, ratio = agretopicity_component(5000.0, 50.0, AgretopicityCfg())
        assert score == 0.0
        assert ratio == 0.01

    def test_identical_binding_scores_in_between(self):
        """A mutant presented exactly as well as the wild type is a poor target."""
        score, ratio = agretopicity_component(100.0, 100.0, AgretopicityCfg())
        assert ratio == 1.0
        assert 0.0 < score < 1.0

    def test_missing_wildtype_scores_neutral_not_zero(self):
        """Absence of a measurement is not evidence the mutation did nothing."""
        cfg = AgretopicityCfg()
        score, ratio = agretopicity_component(50.0, None, cfg)
        assert score == cfg.missing_wt_score
        assert ratio is None

    @pytest.mark.parametrize("mut,wt", [(0.0, 100.0), (-1.0, 100.0), (100.0, 0.0)])
    def test_non_positive_affinities_do_not_explode(self, mut, wt):
        score, ratio = agretopicity_component(mut, wt, AgretopicityCfg())
        assert 0.0 <= score <= 1.0
        assert ratio is None


class TestQuality:
    def test_clean_peptide_scores_one(self):
        assert quality_component("SIINFEKL", QualityCfg()) == 1.0

    def test_cysteines_penalised_per_residue(self):
        cfg = QualityCfg()
        assert quality_component("CIINFEKL", cfg) == pytest.approx(1 - cfg.cysteine_per_residue)
        assert quality_component("CCINFEKL", cfg) == pytest.approx(1 - 2 * cfg.cysteine_per_residue)

    def test_glycosylation_motif_penalised(self):
        assert quality_component("NTSNFEKL", QualityCfg()) < 1.0

    def test_glycosylation_motif_excludes_proline(self):
        """The sequon is N-{P}-[ST]: a proline in the middle blocks it."""
        assert quality_component("NPSNFEKL", QualityCfg()) == 1.0

    def test_floors_at_zero(self):
        assert quality_component("CCCCCCCCC", QualityCfg()) == 0.0


class TestExpression:
    def test_missing_expression_scores_neutral(self):
        cfg = ExpressionCfg()
        assert expression_component(None, cfg) == cfg.missing_value_score

    def test_percentile_passed_through_and_clamped(self):
        cfg = ExpressionCfg()
        assert expression_component(0.75, cfg) == 0.75
        assert expression_component(1.5, cfg) == 1.0
        assert expression_component(-0.5, cfg) == 0.0


def test_presentation_clamped():
    assert presentation_component(1.5) == 1.0
    assert presentation_component(-0.2) == 0.0


def test_combine_is_a_weighted_sum():
    weights = {"presentation": 0.4, "agretopicity": 0.25, "expression": 0.25, "quality": 0.1}
    components = combine(1.0, 0.0, 1.0, 1.0, weights)
    assert components.total == pytest.approx(0.75)


class TestGates:
    def test_passes_when_within_both_limits(self):
        ok, reason = passes_gates(0.5, 100.0, GatesCfg())
        assert ok and reason is None

    def test_fails_on_presentation_percentile(self):
        ok, reason = passes_gates(50.0, 10.0, GatesCfg())
        assert not ok and reason == "gate_presentation_percentile"

    def test_fails_on_affinity(self):
        ok, reason = passes_gates(0.5, 50_000.0, GatesCfg())
        assert not ok and reason == "gate_affinity"


class TestWeightValidation:
    def test_weights_must_sum_to_one(self):
        with pytest.raises(Exception, match=r"sum to 1\.0"):
            ScoringCfg(weights={"presentation": 0.5, "agretopicity": 0.5,
                                "expression": 0.5, "quality": 0.5})

    def test_weights_must_have_exactly_the_right_keys(self):
        with pytest.raises(Exception, match="exactly the keys"):
            ScoringCfg(weights={"presentation": 1.0})

    def test_valid_weights_accepted(self):
        cfg = ScoringCfg(weights={"presentation": 0.4, "agretopicity": 0.25,
                                  "expression": 0.25, "quality": 0.1})
        assert sum(cfg.weights.values()) == pytest.approx(1.0)
