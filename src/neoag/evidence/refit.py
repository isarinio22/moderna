"""Refit survival statistics on the reconstructed data."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test, proportional_hazard_test

from neoag.evidence.published import Arm


@dataclass(frozen=True)
class SurvivalEstimate:
    """Survival at one timepoint, with a Greenwood standard error."""

    time_months: float
    survival: float
    se: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class ProportionalHazardsCheck:
    """Whether a single hazard ratio is a fair summary of the whole follow-up.

    A hazard ratio assumes the two arms' risk stays in constant proportion. If it
    does not, one number hides the shape of the difference.

    With around fifty events this test has very little power, so a non-significant
    result means *we could not detect* a violation, not that none exists. That
    distinction is carried in :attr:`caveat` so it travels with the number.
    """

    p_value: float
    violated: bool
    n_events: int
    caveat: str


@dataclass(frozen=True)
class RefitResult:
    """Everything refitted from the reconstructed data."""

    hazard_ratio: float
    ci_low: float
    ci_high: float
    p_value_two_sided: float
    p_value_one_sided: float
    logrank_p: float
    events: dict[Arm, int]
    n: dict[Arm, int]
    median_survival: dict[Arm, float | None]
    landmarks: dict[Arm, dict[float, SurvivalEstimate]] = field(default_factory=dict)
    proportional_hazards: ProportionalHazardsCheck | None = None
    _fitters: dict[Arm, KaplanMeierFitter] = field(default_factory=dict, repr=False)

    def fitter(self, arm: Arm) -> KaplanMeierFitter:
        return self._fitters[arm]


def greenwood_estimate(fitter: KaplanMeierFitter, t: float, z: float = 1.96) -> SurvivalEstimate:
    """Survival at ``t`` with Greenwood's standard error and a log-log interval.

    The log-log transform is what keeps the interval inside [0, 1]; it is also
    what trial publications use, so our intervals are comparable to theirs.
    """
    table = fitter.event_table
    rows = table[table.index <= t]
    survival = float(fitter.predict(t))

    total = 0.0
    for _, row in rows.iterrows():
        at_risk, observed = float(row["at_risk"]), float(row["observed"])
        if at_risk > 0 and observed > 0 and at_risk != observed:
            total += observed / (at_risk * (at_risk - observed))

    se = survival * math.sqrt(total) if survival > 0 else 0.0
    if 0.0 < survival < 1.0 and total > 0:
        # Interval on the log(-log S) scale, then transformed back.
        log_se = math.sqrt(total) / abs(math.log(survival))
        centre = math.log(-math.log(survival))
        low = math.exp(-math.exp(centre + z * log_se))
        high = math.exp(-math.exp(centre - z * log_se))
    else:
        low = high = survival
    return SurvivalEstimate(t, survival, se, low, high)


def refit(
    data: pd.DataFrame, landmark_months: tuple[float, ...] = (18.0, 24.0, 36.0, 48.0, 60.0)
) -> RefitResult:
    """Fit Kaplan-Meier curves and a Cox model to reconstructed data."""
    cox = CoxPHFitter().fit(
        data[["time_months", "event", "treated"]], "time_months", "event"
    )
    hazard_ratio = float(np.exp(cox.params_["treated"]))
    ci_low, ci_high = (float(x) for x in np.exp(cox.confidence_intervals_.loc["treated"].values))
    p_two = float(cox.summary.loc["treated", "p"])

    combo = data[data.arm == "combo"]
    control = data[data.arm == "control"]
    lr = logrank_test(combo.time_months, control.time_months, combo.event, control.event)

    fitters: dict[Arm, KaplanMeierFitter] = {}
    landmarks: dict[Arm, dict[float, SurvivalEstimate]] = {}
    medians: dict[Arm, float | None] = {}
    events: dict[Arm, int] = {}
    counts: dict[Arm, int] = {}

    for arm, subset in (("combo", combo), ("control", control)):
        fitter = KaplanMeierFitter().fit(subset.time_months, subset.event, label=arm)
        fitters[arm] = fitter
        median = fitter.median_survival_time_
        medians[arm] = None if not np.isfinite(median) else float(median)
        landmarks[arm] = {t: greenwood_estimate(fitter, t) for t in landmark_months}
        events[arm] = int(subset.event.sum())
        counts[arm] = len(subset)

    n_events = int(data.event.sum())
    ph_result = proportional_hazard_test(cox, data[["time_months", "event", "treated"]])
    ph_p = float(np.atleast_1d(ph_result.p_value)[0])
    ph = ProportionalHazardsCheck(
        p_value=ph_p,
        violated=ph_p < 0.05,
        n_events=n_events,
        caveat=(
            f"Tested on {n_events} events, which gives this check very little power. "
            "A non-significant result means no violation was detected, not that the "
            "assumption holds."
        ),
    )

    # The trial's own test was one-sided in the direction of benefit.
    p_one = p_two / 2 if hazard_ratio < 1 else 1 - p_two / 2

    return RefitResult(
        hazard_ratio=hazard_ratio,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value_two_sided=p_two,
        p_value_one_sided=p_one,
        logrank_p=float(lr.p_value),
        events=events,
        n=counts,
        median_survival=medians,
        landmarks=landmarks,
        proportional_hazards=ph,
        _fitters=fitters,
    )
