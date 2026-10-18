"""Quantities a person can actually picture.

A hazard ratio of 0.51 tells almost nobody anything. "Out of 100 people like
this, roughly 20 more were still cancer-free after five years" tells almost
anybody something. This module converts between the two, carefully.

The care matters most for number needed to treat, which has a trap in it. NNT is
one divided by the absolute risk difference. When the difference's confidence
interval includes zero, dividing by it does not produce an interval -- it
produces two separate ranges running off to infinity in both directions.
Published papers get this wrong routinely, printing things like "NNT 5 (95% CI
3 to -41)", which is meaningless. Here the result type simply cannot express a
finite upper bound when the interval crosses zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from lifelines import KaplanMeierFitter
from lifelines.utils import restricted_mean_survival_time

from neoag.evidence.refit import SurvivalEstimate, greenwood_estimate


@dataclass(frozen=True)
class RiskDifference:
    """Absolute difference in the chance of being event-free at one timepoint."""

    time_months: float
    treated_survival: float
    control_survival: float
    difference: float
    se: float
    ci_low: float
    ci_high: float

    @property
    def crosses_zero(self) -> bool:
        return self.ci_low <= 0.0 <= self.ci_high

    @property
    def per_100(self) -> float:
        """How many more people per 100 are event-free. The number for the icon array."""
        return self.difference * 100.0


@dataclass(frozen=True)
class NumberNeededToTreat:
    """How many people would need the treatment for one extra person to benefit.

    ``ci_crosses_zero`` is the important flag. When it is true the reciprocal of
    the confidence interval is *not* an interval, and this type deliberately
    offers no field that could be mistaken for a finite upper bound. Render it
    with :attr:`display` and nothing else.
    """

    time_months: float
    point_estimate: float | None
    kind: Literal["benefit", "harm", "no_difference"]
    ci_crosses_zero: bool
    benefit_bound: float | None
    harm_bound: float | None

    @property
    def display(self) -> str:
        """The only representation of this result that is safe to show."""
        if self.point_estimate is None:
            return "not estimable (no difference at this timepoint)"
        point = f"{self.point_estimate:.1f}"
        if not self.ci_crosses_zero:
            low = f"{self.benefit_bound:.1f}" if self.benefit_bound else "?"
            high = f"{self.harm_bound:.1f}" if self.harm_bound else "?"
            return f"{point} (95% CI {low} to {high})"
        parts = []
        if self.benefit_bound is not None:
            parts.append(f"{self.benefit_bound:.1f} to infinity to benefit one person")
        if self.harm_bound is not None:
            parts.append(f"{self.harm_bound:.1f} to infinity to harm one person")
        return f"{point}, but the interval includes no difference: " + ", or ".join(parts)


@dataclass(frozen=True)
class RelativeRiskReduction:
    """Proportional reduction in the chance of the event."""

    time_months: float
    reduction: float
    ci_low: float
    ci_high: float

    @property
    def percent(self) -> float:
        return self.reduction * 100.0


@dataclass(frozen=True)
class RestrictedMeanDifference:
    """Extra event-free time over a fixed window, in months.

    Needs no proportional-hazards assumption and is in units people understand,
    which makes it the honest companion to a hazard ratio.
    """

    horizon_months: float
    treated_months: float
    control_months: float
    difference_months: float


def absolute_risk_difference(
    treated: KaplanMeierFitter, control: KaplanMeierFitter, t: float, z: float = 1.96
) -> RiskDifference:
    """Difference of two Kaplan-Meier estimates, with a Greenwood interval.

    The interval is built on the untransformed difference. The log-log transform
    used for single-arm survival is not additive, so it cannot be applied to a
    difference -- a detail that is easy to get wrong.
    """
    a: SurvivalEstimate = greenwood_estimate(treated, t, z)
    b: SurvivalEstimate = greenwood_estimate(control, t, z)
    difference = a.survival - b.survival
    se = math.sqrt(a.se**2 + b.se**2)
    return RiskDifference(
        time_months=t,
        treated_survival=a.survival,
        control_survival=b.survival,
        difference=difference,
        se=se,
        ci_low=difference - z * se,
        ci_high=difference + z * se,
    )


def number_needed_to_treat(rd: RiskDifference) -> NumberNeededToTreat:
    """Convert a risk difference into NNT, handling the infinite-interval case."""
    if rd.difference == 0:
        return NumberNeededToTreat(
            rd.time_months, None, "no_difference", rd.crosses_zero, None, None
        )

    point = abs(1.0 / rd.difference)
    kind: Literal["benefit", "harm"] = "benefit" if rd.difference > 0 else "harm"

    benefit_bound = 1.0 / rd.ci_high if rd.ci_high > 0 else None
    harm_bound = 1.0 / abs(rd.ci_low) if rd.ci_low < 0 else None

    if not rd.crosses_zero:
        # Both bounds have the same sign, so the reciprocal really is an interval.
        low, high = sorted((abs(1.0 / rd.ci_low), abs(1.0 / rd.ci_high)))
        return NumberNeededToTreat(rd.time_months, point, kind, False, low, high)

    return NumberNeededToTreat(rd.time_months, point, kind, True, benefit_bound, harm_bound)


def relative_risk_reduction(
    treated: KaplanMeierFitter, control: KaplanMeierFitter, t: float,
    n_boot: int = 2000, seed: int = 20251215,
) -> RelativeRiskReduction:
    """Proportional reduction in event risk, with a bootstrap interval.

    The ratio of two risks has an awkward distribution, so the interval comes
    from resampling rather than a delta-method approximation.
    """
    treated_risk = 1.0 - float(treated.predict(t))
    control_risk = 1.0 - float(control.predict(t))
    point = 1.0 - treated_risk / control_risk if control_risk > 0 else float("nan")

    rng = np.random.default_rng(seed)
    samples = []
    for fitter in (treated, control):
        durations = np.asarray(fitter.durations)
        observed = np.asarray(fitter.event_observed)
        draws = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(durations), len(durations))
            k = KaplanMeierFitter().fit(durations[idx], observed[idx])
            draws.append(1.0 - float(k.predict(t)))
        samples.append(np.asarray(draws))

    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = 1.0 - samples[0] / samples[1]
    ratios = ratios[np.isfinite(ratios)]
    low, high = (float(x) for x in np.percentile(ratios, [2.5, 97.5]))
    return RelativeRiskReduction(t, point, low, high)


def restricted_mean_difference(
    treated: KaplanMeierFitter, control: KaplanMeierFitter, horizon_months: float = 60.0
) -> RestrictedMeanDifference:
    """Average event-free months gained over a fixed window."""
    a = float(restricted_mean_survival_time(treated, t=horizon_months))
    b = float(restricted_mean_survival_time(control, t=horizon_months))
    return RestrictedMeanDifference(horizon_months, a, b, a - b)
