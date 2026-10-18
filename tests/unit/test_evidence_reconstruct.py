"""Reconstruction of patient-level data from published summary tables."""

from __future__ import annotations

import pytest

from neoag.evidence.published import (
    AT_RISK_RFS_5YR,
    RFS_5YEAR,
    AtRiskTable,
    RefusedReconstruction,
    assert_reconstructible,
)
from neoag.evidence.reconstruct import (
    ReconstructionError,
    interval_counts,
    placement_sensitivity,
    reconstruct,
    reconstruct_arm,
)


class TestIntervalCounts:
    """The published censoring column forces the event counts by arithmetic."""

    def test_event_totals_match_the_published_totals_exactly(self):
        """A constraint we did not choose and cannot tune: it either closes or it doesn't."""
        for arm, table in AT_RISK_RFS_5YR.items():
            derived = sum(i.events for i in interval_counts(table))
            assert derived == RFS_5YEAR.events[arm]

    def test_every_patient_is_accounted_for(self):
        for table in AT_RISK_RFS_5YR.values():
            intervals = interval_counts(table)
            total = sum(i.events for i in intervals) + sum(i.censored for i in intervals)
            assert total == table.n_randomised

    def test_combination_arm_interval_events(self):
        """Pinned so a future edit to the table cannot silently change the analysis."""
        counts = [i.events for i in interval_counts(AT_RISK_RFS_5YR["combo"])]
        assert counts == [13, 3, 4, 2, 2, 2, 0, 1, 0, 1, 0]

    def test_control_arm_interval_events(self):
        counts = [i.events for i in interval_counts(AT_RISK_RFS_5YR["control"])]
        assert counts == [7, 4, 7, 1, 2, 0, 0, 2, 0, 0, 0]

    def test_table_without_censoring_column_is_refused_not_guessed(self):
        table = AtRiskTable(times_months=(0.0, 6.0, 12.0), n_risk=(100, 80, 60))
        with pytest.raises(ReconstructionError, match="not determined"):
            interval_counts(table)

    def test_inconsistent_table_raises(self):
        """More censorings than patients lost means the published columns disagree."""
        table = AtRiskTable(
            times_months=(0.0, 6.0), n_risk=(100, 90), n_censored_cumulative=(0, 20)
        )
        with pytest.raises(ReconstructionError, match="negative count"):
            interval_counts(table)


class TestReconstruction:
    def test_produces_one_record_per_patient(self):
        data = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
        assert len(data) == 157
        assert (data.arm == "combo").sum() == 107
        assert (data.arm == "control").sum() == 50

    def test_event_counts_survive_reconstruction(self):
        data = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
        for arm, expected in RFS_5YEAR.events.items():
            assert int(data[data.arm == arm].event.sum()) == expected

    def test_wrong_expected_total_fails_loudly(self):
        """If the derived counts disagree with the publication, stop."""
        with pytest.raises(ReconstructionError, match="does not reproduce the trial"):
            reconstruct_arm("combo", AT_RISK_RFS_5YR["combo"], expected_events=99)

    def test_all_times_lie_inside_the_follow_up_window(self):
        data = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
        assert data.time_months.min() >= 0
        assert data.time_months.max() <= 66

    def test_is_deterministic(self):
        a = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
        b = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
        assert a.equals(b)

    @pytest.mark.parametrize("placement", ["uniform", "early", "late", "start"])
    def test_placement_never_changes_the_counts(self, placement):
        """Placement moves events in time; it must not create or destroy any."""
        data = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events, placement)
        assert int(data.event.sum()) == 51
        assert len(data) == 157


class TestSensitivity:
    def test_hazard_ratio_barely_moves_across_placements(self):
        """The one assumption the reconstruction makes should not drive the answer."""
        sensitivity = placement_sensitivity(AT_RISK_RFS_5YR, RFS_5YEAR.events)
        assert len(sensitivity.results) == 4
        assert sensitivity.spread < 0.02
        for hr in sensitivity.results.values():
            assert abs(hr - RFS_5YEAR.hazard_ratio) < 0.03


class TestRefusals:
    def test_overall_survival_is_refused(self):
        """Fourteen deaths drawn as curves would look like a finding. It is noise."""
        with pytest.raises(RefusedReconstruction, match="7 deaths"):
            assert_reconstructible("OS")

    def test_three_year_cut_is_refused(self):
        with pytest.raises(RefusedReconstruction, match="fabrication"):
            assert_reconstructible("RFS", "year3")

    def test_five_year_recurrence_is_allowed(self):
        assert_reconstructible("RFS", "year5")

    def test_no_at_risk_table_exists_for_overall_survival(self):
        """The refusal is structural, not merely a check that could be bypassed."""
        from neoag.evidence import published

        assert not hasattr(published, "AT_RISK_OS_5YR")
