"""Compare the reconstruction against the published values, and publish the gaps.

A reconstruction that is not checked against what it claims to reproduce is
worthless. This module produces a signed discrepancy table -- reconstructed
minus published, for every quantity the trial reported -- and the project
publishes it rather than summarising it as "good agreement".

Tolerances are set once, here, in advance. Widening one because a check failed
would defeat the purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from neoag.evidence.published import PublishedResult
from neoag.evidence.refit import RefitResult

Status = Literal["exact", "pass", "warn", "fail"]


@dataclass(frozen=True)
class Check:
    """One comparison between a reconstructed and a published value."""

    name: str
    reconstructed: float | None
    published: float | None
    tolerance: float | None
    status: Status
    note: str = ""

    @property
    def difference(self) -> float | None:
        if self.reconstructed is None or self.published is None:
            return None
        return self.reconstructed - self.published

    def format_row(self) -> str:
        mark = {"exact": "=", "pass": "ok", "warn": "!", "fail": "X"}[self.status]
        if self.reconstructed is None or self.published is None:
            return f"| {self.name} | - | - | - | {mark} |"
        diff = self.difference or 0.0
        return (
            f"| {self.name} | {self.reconstructed:.4g} | {self.published:.4g} "
            f"| {diff:+.4g} | {mark} |"
        )


@dataclass(frozen=True)
class ValidationReport:
    checks: tuple[Check, ...]

    @property
    def failures(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if c.status == "fail")

    @property
    def warnings(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if c.status == "warn")

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_markdown(self) -> str:
        lines = [
            "| quantity | reconstructed | published | difference | |",
            "|---|---:|---:|---:|:--:|",
            *(c.format_row() for c in self.checks),
        ]
        return "\n".join(lines)


#: Tolerances, fixed in advance. ``None`` means the values must match exactly.
TOLERANCES: dict[str, float | None] = {
    "n (combination)": None,
    "n (control)": None,
    "events (combination)": None,
    "events (control)": None,
    "hazard ratio": 0.030,
    "95% CI lower": 0.040,
    "95% CI upper": 0.070,
    "one-sided p": 0.005,
    "median RFS (control, months)": 2.5,
}
#: Landmark survival estimates, in absolute proportion.
LANDMARK_TOLERANCE = 0.015


def _check(name: str, got: float | None, want: float | None, tol: float | None) -> Check:
    if got is None or want is None:
        return Check(name, got, want, tol, "warn", "not published or not estimated")
    if tol is None:
        status: Status = "exact" if got == want else "fail"
        return Check(name, got, want, None, status)
    difference = abs(got - want)
    if difference <= tol * 0.5:
        return Check(name, got, want, tol, "pass")
    if difference <= tol:
        return Check(name, got, want, tol, "warn", "within tolerance but drifting")
    return Check(name, got, want, tol, "fail", f"exceeds tolerance of {tol}")


def validate(refit_result: RefitResult, published: PublishedResult) -> ValidationReport:
    """Build the full discrepancy table."""
    checks: list[Check] = [
        _check("n (combination)", refit_result.n["combo"], published.n["combo"], None),
        _check("n (control)", refit_result.n["control"], published.n["control"], None),
        _check("events (combination)", refit_result.events["combo"],
               published.events["combo"], None),
        _check("events (control)", refit_result.events["control"],
               published.events["control"], None),
        _check("hazard ratio", refit_result.hazard_ratio, published.hazard_ratio,
               TOLERANCES["hazard ratio"]),
        _check("95% CI lower", refit_result.ci_low, published.ci_low,
               TOLERANCES["95% CI lower"]),
        _check("95% CI upper", refit_result.ci_high, published.ci_high,
               TOLERANCES["95% CI upper"]),
    ]

    if published.p_value is not None and published.p_value_sided == "one":
        checks.append(
            _check("one-sided p", refit_result.p_value_one_sided, published.p_value,
                   TOLERANCES["one-sided p"])
        )

    for arm in ("combo", "control"):
        label = "combination" if arm == "combo" else "control"
        for t, want in sorted(published.landmarks.get(arm, {}).items()):
            got = refit_result.landmarks.get(arm, {}).get(t)
            checks.append(
                _check(f"{label} survival at {t:.0f} months",
                       got.survival if got else None, want, LANDMARK_TOLERANCE)
            )

    for arm, want in published.median_survival.items():
        got = refit_result.median_survival.get(arm)
        label = "combination" if arm == "combo" else "control"
        if want is None:
            # "Not estimable" is a real published result: more than half the arm
            # never had the event. Producing a finite median would be a failure.
            status: Status = "exact" if got is None else "fail"
            checks.append(
                Check(f"median RFS ({label})", got, None, None, status,
                      "published as not estimable; a finite value would contradict it")
            )
        else:
            checks.append(
                _check(f"median RFS ({label}, months)", got, want,
                       TOLERANCES["median RFS (control, months)"])
            )

    return ValidationReport(tuple(checks))
