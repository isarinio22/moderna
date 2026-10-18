"""Reconstruct patient-level data from a published Kaplan-Meier at-risk table.

Published trials report curves and summary tables, not the individual patient
records behind them. Reconstructing approximate patient-level data lets anyone
refit the statistics and check the published claims, which is the difference
between reading a result and examining one.

The usual method (Guyot et al., *BMC Med Res Methodol* 2012;12:9) digitises the
drawn curve and solves iteratively for how many events must have occurred in
each interval, because only the at-risk column is normally published.

**This trial published more than usual.** Its five-year figure reports
*cumulative censored* counts alongside patients at risk, and those two columns
force the event count in each interval by arithmetic:

    events = n_risk[i] - n_risk[i+1] - censored_during_interval

No iteration, no curve fitting, no reading values off a picture. The counts are
determined, and they are checkable: they must sum to the separately published
total number of events, which is a constraint we did not choose and cannot tune.

The one genuine assumption left is *where inside each interval* the events fall.
Events are spread evenly through the interval; censorings are placed in its
latter half, because a patient recorded as censored at a visit was event-free at
that visit. :func:`placement_sensitivity` reports how much the answer moves
under other choices -- for this trial, very little.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

from neoag.evidence.published import Arm, AtRiskTable

Placement = Literal["uniform", "early", "late", "start"]


class ReconstructionError(Exception):
    """The published table is not internally consistent."""


@dataclass(frozen=True)
class Interval:
    """One row of the reconstruction: what happened between two timepoints."""

    start_months: float
    end_months: float
    n_at_risk: int
    events: int
    censored: int


@dataclass(frozen=True)
class ArmReconstruction:
    """Reconstructed records for one treatment arm."""

    arm: Arm
    intervals: tuple[Interval, ...]
    times: tuple[float, ...]
    events: tuple[int, ...]
    placement: Placement

    @property
    def n(self) -> int:
        return len(self.times)

    @property
    def total_events(self) -> int:
        return sum(self.events)


def interval_counts(table: AtRiskTable) -> tuple[Interval, ...]:
    """Derive events and censorings per interval from the published table.

    Exact when the table carries a cumulative censored column. Raises rather
    than guessing if it does not, or if the arithmetic yields a negative count --
    which would mean the published table is internally inconsistent.
    """
    if table.n_censored_cumulative is None:
        raise ReconstructionError(
            "this table has no cumulative censored column, so interval event counts "
            "are not determined. Reconstructing it would require digitising the "
            "published curve, which this project does not do."
        )

    out: list[Interval] = []
    for i in range(len(table.times_months) - 1):
        censored = table.n_censored_cumulative[i + 1] - table.n_censored_cumulative[i]
        events = table.n_risk[i] - table.n_risk[i + 1] - censored
        if events < 0 or censored < 0:
            raise ReconstructionError(
                f"interval {table.times_months[i]}-{table.times_months[i + 1]} months "
                f"implies {events} events and {censored} censorings. A negative count "
                "means the published at-risk and censored columns disagree."
            )
        out.append(
            Interval(
                start_months=table.times_months[i],
                end_months=table.times_months[i + 1],
                n_at_risk=table.n_risk[i],
                events=events,
                censored=censored,
            )
        )
    return tuple(out)


def _event_time(start: float, end: float, k: int, total: int, placement: Placement) -> float:
    span = end - start
    if placement == "uniform":
        return start + span * (k + 0.5) / total
    if placement == "early":
        return start + span * 0.5 * (k + 1) / (total + 1)
    if placement == "late":
        return start + span * (0.5 + 0.5 * (k + 1) / (total + 1))
    return start + span * 0.001 * (k + 1)  # "start"


def reconstruct_arm(
    arm: Arm, table: AtRiskTable, expected_events: int | None = None,
    placement: Placement = "uniform",
) -> ArmReconstruction:
    """Rebuild one arm's patient records from its at-risk table.

    ``expected_events`` is the separately published total. It is checked, not
    used: if the derived counts do not sum to it, the reconstruction is wrong and
    should fail loudly rather than quietly produce a plausible curve.
    """
    intervals = interval_counts(table)
    derived_events = sum(i.events for i in intervals)
    derived_censored = sum(i.censored for i in intervals)

    if expected_events is not None and derived_events != expected_events:
        raise ReconstructionError(
            f"{arm}: table implies {derived_events} events but the publication "
            f"reports {expected_events}. The reconstruction does not reproduce the "
            "trial and must not be used."
        )
    if derived_events + derived_censored != table.n_randomised:
        raise ReconstructionError(
            f"{arm}: {derived_events} events plus {derived_censored} censored does not "
            f"account for all {table.n_randomised} patients."
        )

    times: list[float] = []
    events: list[int] = []
    for interval in intervals:
        for k in range(interval.events):
            times.append(_event_time(interval.start_months, interval.end_months,
                                     k, interval.events, placement))
            events.append(1)
        for k in range(interval.censored):
            span = interval.end_months - interval.start_months
            if placement == "start":
                offset = span * (k + 0.5) / interval.censored
            else:
                # A patient censored at a visit was event-free at that visit, so
                # censorings sit in the latter half of the interval.
                offset = span * (0.5 + 0.5 * (k + 0.5) / interval.censored)
            times.append(interval.start_months + offset)
            events.append(0)

    order = sorted(range(len(times)), key=lambda i: (times[i], -events[i]))
    return ArmReconstruction(
        arm=arm,
        intervals=intervals,
        times=tuple(times[i] for i in order),
        events=tuple(events[i] for i in order),
        placement=placement,
    )


def reconstruct(
    tables: dict[Arm, AtRiskTable],
    expected_events: dict[Arm, int] | None = None,
    placement: Placement = "uniform",
) -> pd.DataFrame:
    """Reconstruct both arms into one tidy frame.

    Columns: ``arm``, ``time_months``, ``event`` (1 = recurrence, 0 = censored),
    ``treated`` (1 for the combination arm).
    """
    frames = []
    for arm, table in tables.items():
        expected = (expected_events or {}).get(arm)
        rec = reconstruct_arm(arm, table, expected, placement)
        frames.append(
            pd.DataFrame(
                {
                    "arm": arm,
                    "time_months": rec.times,
                    "event": rec.events,
                    "treated": 1 if arm == "combo" else 0,
                }
            )
        )
    return pd.concat(frames, ignore_index=True).sort_values(
        ["arm", "time_months"], kind="stable"
    ).reset_index(drop=True)


@dataclass(frozen=True)
class PlacementSensitivity:
    """How much the answer depends on where events fall inside each interval.

    The interval counts are forced by the published table, so this is the only
    assumption the reconstruction makes. Reporting its influence is what lets a
    reader judge whether the assumption mattered.
    """

    results: dict[Placement, float]

    @property
    def spread(self) -> float:
        values = list(self.results.values())
        return max(values) - min(values)

    def format_table(self) -> str:
        rows = "\n".join(
            f"| {k} | {v:.4f} |" for k, v in sorted(self.results.items(), key=lambda kv: kv[1])
        )
        return f"| event placement | hazard ratio |\n|---|---:|\n{rows}"


def placement_sensitivity(
    tables: dict[Arm, AtRiskTable], expected_events: dict[Arm, int] | None = None
) -> PlacementSensitivity:
    """Refit the hazard ratio under every event-placement rule."""
    results: dict[Placement, float] = {}
    for placement in ("start", "early", "uniform", "late"):
        data = reconstruct(tables, expected_events, placement)  # type: ignore[arg-type]
        cox = CoxPHFitter().fit(
            data[["time_months", "event", "treated"]], "time_months", "event"
        )
        results[placement] = float(np.exp(cox.params_["treated"]))  # type: ignore[index]
    return PlacementSensitivity(results)
