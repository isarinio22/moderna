"""Refitted statistics, derived quantities, and the validation report."""

from __future__ import annotations

import pytest

from neoag.evidence.derived import (
    RiskDifference,
    absolute_risk_difference,
    number_needed_to_treat,
    restricted_mean_difference,
)
from neoag.evidence.honesty import BANNED_PHRASES, EXPLAINERS, check_text, verdict
from neoag.evidence.published import AT_RISK_RFS_5YR, RFS_5YEAR
from neoag.evidence.reconstruct import reconstruct
from neoag.evidence.refit import greenwood_estimate, refit
from neoag.evidence.validate import validate


@pytest.fixture(scope="module")
def fitted():
    return refit(reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events))


class TestReproducesPublishedResults:
    """The whole point: does the reconstruction actually reproduce the trial?"""

    def test_hazard_ratio(self, fitted):
        assert abs(fitted.hazard_ratio - RFS_5YEAR.hazard_ratio) < 0.030

    def test_confidence_interval(self, fitted):
        assert abs(fitted.ci_low - RFS_5YEAR.ci_low) < 0.040
        assert abs(fitted.ci_high - RFS_5YEAR.ci_high) < 0.070

    def test_hazard_ratio_lies_inside_the_published_interval(self, fitted):
        assert RFS_5YEAR.ci_low < fitted.hazard_ratio < RFS_5YEAR.ci_high

    def test_one_sided_p_value(self, fitted):
        assert abs(fitted.p_value_one_sided - RFS_5YEAR.p_value) < 0.005

    def test_event_counts_are_exact(self, fitted):
        assert fitted.events == RFS_5YEAR.events

    @pytest.mark.parametrize("arm", ["combo", "control"])
    def test_landmark_survival(self, fitted, arm):
        for t, published in RFS_5YEAR.landmarks[arm].items():
            assert abs(fitted.landmarks[arm][t].survival - published) < 0.015

    def test_combination_median_stays_not_estimable(self, fitted):
        """Published as not estimable: producing a number would contradict the trial."""
        assert fitted.median_survival["combo"] is None

    def test_control_median_is_close(self, fitted):
        assert abs(fitted.median_survival["control"] - 44.65) < 2.5


class TestGreenwood:
    def test_survival_starts_at_one(self, fitted):
        assert greenwood_estimate(fitted.fitter("combo"), 0.0).survival == pytest.approx(1.0)

    def test_interval_stays_inside_zero_to_one(self, fitted):
        for arm in ("combo", "control"):
            for t in (6.0, 18.0, 36.0, 60.0):
                estimate = greenwood_estimate(fitted.fitter(arm), t)
                assert 0.0 <= estimate.ci_low <= estimate.survival <= estimate.ci_high <= 1.0

    def test_uncertainty_grows_with_follow_up(self, fitted):
        early = greenwood_estimate(fitted.fitter("control"), 12.0)
        late = greenwood_estimate(fitted.fitter("control"), 60.0)
        assert late.se > early.se


class TestNumberNeededToTreat:
    """NNT is where published papers most often print something meaningless."""

    def test_clear_benefit_gives_an_ordinary_interval(self):
        rd = RiskDifference(60.0, 0.70, 0.50, 0.20, 0.05, 0.10, 0.30)
        nnt = number_needed_to_treat(rd)
        assert not nnt.ci_crosses_zero
        assert nnt.kind == "benefit"
        assert nnt.point_estimate == pytest.approx(5.0)
        assert "infinity" not in nnt.display

    def test_interval_crossing_zero_is_not_an_interval(self):
        """The reciprocal of a range spanning zero is two rays, not a range.

        A naive implementation prints 'NNT 10 (95% CI 5 to -20)', which is
        meaningless. This type cannot express that.
        """
        rd = RiskDifference(60.0, 0.55, 0.45, 0.10, 0.08, -0.05, 0.20)
        nnt = number_needed_to_treat(rd)
        assert nnt.ci_crosses_zero
        assert nnt.benefit_bound == pytest.approx(5.0)
        assert nnt.harm_bound == pytest.approx(20.0)
        assert "infinity" in nnt.display
        assert "benefit" in nnt.display and "harm" in nnt.display

    def test_no_field_can_be_mistaken_for_a_finite_upper_bound(self):
        rd = RiskDifference(60.0, 0.55, 0.45, 0.10, 0.08, -0.05, 0.20)
        nnt = number_needed_to_treat(rd)
        assert not hasattr(nnt, "ci_high")
        assert not hasattr(nnt, "upper_bound")

    def test_zero_difference_is_not_estimable(self):
        rd = RiskDifference(60.0, 0.5, 0.5, 0.0, 0.05, -0.10, 0.10)
        nnt = number_needed_to_treat(rd)
        assert nnt.point_estimate is None
        assert nnt.kind == "no_difference"
        assert "not estimable" in nnt.display

    def test_harm_direction_is_labelled(self):
        rd = RiskDifference(60.0, 0.40, 0.60, -0.20, 0.05, -0.30, -0.10)
        nnt = number_needed_to_treat(rd)
        assert nnt.kind == "harm"
        assert nnt.point_estimate == pytest.approx(5.0)


class TestAbsoluteRiskDifference:
    def test_matches_the_difference_of_published_landmarks(self, fitted):
        rd = absolute_risk_difference(fitted.fitter("combo"), fitted.fitter("control"), 60.0)
        published_difference = (
            RFS_5YEAR.landmarks["combo"][60.0] - RFS_5YEAR.landmarks["control"][60.0]
        )
        assert abs(rd.difference - published_difference) < 0.02

    def test_per_100_is_the_number_for_an_icon_array(self, fitted):
        rd = absolute_risk_difference(fitted.fitter("combo"), fitted.fitter("control"), 60.0)
        assert 10 < rd.per_100 < 30


class TestRestrictedMean:
    def test_reports_extra_event_free_months(self, fitted):
        rmst = restricted_mean_difference(fitted.fitter("combo"), fitted.fitter("control"), 60.0)
        assert 0 < rmst.difference_months < 24
        assert rmst.treated_months > rmst.control_months

    def test_cannot_exceed_the_horizon(self, fitted):
        rmst = restricted_mean_difference(fitted.fitter("combo"), fitted.fitter("control"), 60.0)
        assert rmst.treated_months <= 60.0


class TestProportionalHazards:
    def test_reports_its_own_lack_of_power(self, fitted):
        """A non-significant test here means 'we could not tell', not 'it holds'."""
        ph = fitted.proportional_hazards
        assert ph.n_events == 51
        assert "power" in ph.caveat
        assert "not that the assumption holds" in ph.caveat


class TestValidationReport:
    def test_every_check_passes(self, fitted):
        report = validate(fitted, RFS_5YEAR)
        assert report.passed, [c.name for c in report.failures]

    def test_counts_are_checked_exactly(self, fitted):
        report = validate(fitted, RFS_5YEAR)
        exact = [c for c in report.checks if c.status == "exact"]
        assert any("events" in c.name for c in exact)

    def test_report_renders_as_markdown(self, fitted):
        markdown = validate(fitted, RFS_5YEAR).to_markdown()
        assert markdown.startswith("| quantity |")
        assert "hazard ratio" in markdown

    def test_a_bad_reconstruction_is_caught(self, fitted):
        """Guards the guard: the report must actually be able to fail."""
        broken = fitted.__class__(
            hazard_ratio=0.95, ci_low=0.5, ci_high=1.8, p_value_two_sided=0.8,
            p_value_one_sided=0.4, logrank_p=0.8,
            events={"combo": 28, "control": 23}, n={"combo": 107, "control": 50},
            median_survival={"combo": None, "control": 44.0},
        )
        report = validate(broken, RFS_5YEAR)
        assert not report.passed
        assert any("hazard ratio" in c.name for c in report.failures)


class TestHonesty:
    def test_no_copy_contains_a_banned_phrase(self):
        """Every word this project publishes about the evidence, checked."""
        texts = [verdict()]
        for explainer in EXPLAINERS.values():
            texts += [explainer.title, explainer.plain, explainer.technical, *explainer.caveats]
        for text in texts:
            assert check_text(text) == [], f"banned phrase in: {text[:60]}"

    def test_the_banned_phrase_check_actually_works(self):
        assert check_text("this is a cure for cancer") == ["cure for cancer"]
        for phrase in BANNED_PHRASES:
            assert check_text(f"prefix {phrase} suffix") == [phrase]

    def test_every_explainer_cites_a_source(self):
        for key, explainer in EXPLAINERS.items():
            assert explainer.sources, f"{key} has no source"

    def test_the_one_sided_alpha_is_always_explained_both_ways(self):
        """The headline p-value must never appear without its two-sided counterpart."""
        text = EXPLAINERS["one_sided_alpha"].plain
        assert "0.0266" in text and "0.053" in text

    def test_survival_explainer_refuses_to_overreach(self):
        text = EXPLAINERS["rfs_is_not_survival"].plain.lower()
        assert "not the same as living longer" in text

    def test_verdict_states_both_promise_and_limits(self):
        text = verdict().lower()
        assert "promising" in text and "not proof" in text
        assert "phase 3" in text
