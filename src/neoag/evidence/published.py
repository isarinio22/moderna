"""Published values from KEYNOTE-942, with citations.

Every number here is transcribed from a primary source and cross-referenced in
``research/sources.md``. Nothing is computed, inferred or rounded. This module is
the single place the project states what the trial reported, so the analysis can
be checked against it rather than against a memory of it.

Three analyses are published. **They are the same 157 patients with longer
follow-up, not three studies.** Reporting them as independent confirmations
would be wrong, and the module keeps the data cutoff attached to every number so
that mistake is hard to make.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise
from typing import Literal

Arm = Literal["combo", "control"]
Endpoint = Literal["RFS", "DMFS", "OS"]

#: Arm labels as they should appear to a reader.
ARM_LABELS: dict[Arm, str] = {
    "combo": "mRNA-4157 + pembrolizumab",
    "control": "pembrolizumab alone",
}


@dataclass(frozen=True)
class AtRiskTable:
    """Patients still being followed at each timepoint, from a published figure.

    ``n_censored_cumulative`` is the unusual and valuable part. Most published
    Kaplan-Meier figures give only ``n_risk``, which leaves the number of events
    in each interval to be estimated. With both columns the events are forced by
    arithmetic:

        events = n_risk[i] - n_risk[i+1] - censored_in_interval

    No estimation, no curve fitting, no reading pixels off a figure.
    """

    times_months: tuple[float, ...]
    n_risk: tuple[int, ...]
    n_censored_cumulative: tuple[int, ...] | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if len(self.times_months) != len(self.n_risk):
            raise ValueError("times and n_risk must be the same length")
        if self.n_censored_cumulative is not None:
            if len(self.n_censored_cumulative) != len(self.n_risk):
                raise ValueError("censored column must match n_risk length")
            if any(b < a for a, b in pairwise(self.n_censored_cumulative)):
                raise ValueError("cumulative censored counts must not decrease")
        if any(b > a for a, b in pairwise(self.n_risk)):
            raise ValueError("patients at risk must not increase")

    @property
    def n_randomised(self) -> int:
        return self.n_risk[0]


@dataclass(frozen=True)
class PublishedResult:
    """What one analysis of one endpoint reported."""

    endpoint: Endpoint
    cutoff: str
    median_followup_months: float
    hazard_ratio: float
    ci_low: float
    ci_high: float
    events: dict[Arm, int]
    n: dict[Arm, int]
    p_value: float | None = None
    p_value_sided: Literal["one", "two"] | None = None
    p_value_is_nominal: bool = True
    landmarks: dict[Arm, dict[float, float]] = field(default_factory=dict)
    median_survival: dict[Arm, float | None] = field(default_factory=dict)
    source: str = ""
    note: str = ""


# --------------------------------------------------------------------------- #
# Trial design
# --------------------------------------------------------------------------- #

TRIAL = {
    "name": "KEYNOTE-942 (mRNA-4157-P201)",
    "registration": "NCT03897881",
    "phase": "2b",
    "n_randomised": 157,
    "randomisation_ratio": "2:1",
    "n_combo": 107,
    "n_control": 50,
    "blinding": "open-label",
    "population": "resected stage IIIB-IV cutaneous melanoma",
    "primary_endpoint": "investigator-assessed recurrence-free survival (intention to treat)",
    "neoantigens_encoded": 34,
    # The evidentiary bar the trial set itself, which is looser than the
    # conventional two-sided 0.05 and must be stated whenever the result is.
    "powered_for_hr": 0.5,
    "power": 0.80,
    "alpha": 0.10,
    "alpha_sided": "one",
    "enrolment": "2019-07-18 to 2021-09-30",
    "sites": "United States and Australia",
}


# --------------------------------------------------------------------------- #
# At-risk tables (ASCO 2026 presentation, five-year analysis)
# --------------------------------------------------------------------------- #

_ASCO_2026 = (
    "Carlino et al., ASCO 2026 abstract 9500 and oral presentation; "
    "data cutoff 2025-12-15. Transcribed in research/sources.md section 2.2."
)

AT_RISK_RFS_5YR: dict[Arm, AtRiskTable] = {
    "combo": AtRiskTable(
        times_months=tuple(float(m) for m in range(0, 67, 6)),
        n_risk=(107, 89, 84, 78, 74, 70, 57, 55, 39, 20, 3, 0),
        n_censored_cumulative=(0, 5, 7, 9, 11, 13, 24, 26, 41, 60, 76, 79),
        source=_ASCO_2026,
    ),
    "control": AtRiskTable(
        times_months=tuple(float(m) for m in range(0, 67, 6)),
        n_risk=(50, 41, 37, 29, 27, 22, 19, 17, 12, 7, 3, 0),
        n_censored_cumulative=(0, 2, 2, 3, 4, 7, 10, 12, 15, 20, 24, 27),
        source=_ASCO_2026,
    ),
}


# --------------------------------------------------------------------------- #
# Published results, by data cutoff
# --------------------------------------------------------------------------- #

RFS_PRIMARY = PublishedResult(
    endpoint="RFS",
    cutoff="2022-11-14",
    median_followup_months=23.0,
    hazard_ratio=0.561,
    ci_low=0.309,
    ci_high=1.017,
    events={"combo": 24, "control": 20},
    n={"combo": 107, "control": 50},
    p_value=0.0266,
    p_value_sided="one",
    p_value_is_nominal=False,
    landmarks={"combo": {12.0: 0.834, 18.0: 0.786}, "control": {12.0: 0.771, 18.0: 0.622}},
    source="AACR 2023 abstract CT001; Weber et al., Lancet 2024;403(10427):632-644.",
    note=(
        "The only analysis with a protected significance level. One-sided p = 0.0266 "
        "against a prespecified one-sided alpha of 0.10. The same result two-sided is "
        "p = 0.053, so it met the bar the trial set and would not have met a "
        "conventional two-sided 0.05."
    ),
)

RFS_3YEAR = PublishedResult(
    endpoint="RFS",
    cutoff="2023-11-03",
    median_followup_months=34.9,
    hazard_ratio=0.510,
    ci_low=0.288,
    ci_high=0.906,
    events={"combo": 25, "control": 22},
    n={"combo": 107, "control": 50},
    p_value=0.019,
    p_value_sided="two",
    p_value_is_nominal=True,
    landmarks={"combo": {30.0: 0.748}, "control": {30.0: 0.556}},
    source="ASCO 2024 abstract LBA9512; Carlino et al., JCO Oncol Adv 2026;3(1):e2500008.",
    note=(
        "Nominal. No alpha was assigned to this analysis. No Kaplan-Meier figure with "
        "an at-risk table was published for this cutoff, so it is quoted, never "
        "reconstructed."
    ),
)

RFS_5YEAR = PublishedResult(
    endpoint="RFS",
    cutoff="2025-12-15",
    median_followup_months=60.3,
    hazard_ratio=0.510,
    ci_low=0.294,
    ci_high=0.887,
    events={"combo": 28, "control": 23},
    n={"combo": 107, "control": 50},
    p_value=0.0075,
    p_value_sided="one",
    p_value_is_nominal=True,
    landmarks={
        "combo": {18.0: 0.804, 24.0: 0.783, 36.0: 0.738, 48.0: 0.724, 60.0: 0.688},
        "control": {18.0: 0.622, 24.0: 0.600, 36.0: 0.556, 48.0: 0.491, 60.0: 0.491},
    },
    median_survival={"combo": None, "control": 44.65},
    source="ASCO 2026 abstract 9500; Khattak et al., J Clin Oncol 2026;44(26):2482-2489.",
    note="Nominal. The analysis this project reconstructs, because it publishes a "
         "censoring column that makes the reconstruction exact at interval level.",
)

DMFS_5YEAR = PublishedResult(
    endpoint="DMFS",
    cutoff="2025-12-15",
    median_followup_months=60.3,
    hazard_ratio=0.411,
    ci_low=0.200,
    ci_high=0.843,
    events={"combo": 15, "control": 15},
    n={"combo": 107, "control": 50},
    source="ASCO 2026 abstract 9500.",
    note="Distant metastasis is somewhat less susceptible to open-label ascertainment "
         "bias than recurrence of any kind, since it is harder to miss or dispute.",
)

OS_5YEAR = PublishedResult(
    endpoint="OS",
    cutoff="2025-12-15",
    median_followup_months=60.3,
    hazard_ratio=0.471,
    ci_low=0.165,
    ci_high=1.345,
    events={"combo": 7, "control": 7},
    n={"combo": 107, "control": 50},
    source="ASCO 2026 abstract 9500.",
    note=(
        "Fourteen deaths in the entire trial. A hazard ratio computed on fourteen "
        "events carries almost no information, and the interval includes both a large "
        "benefit and a modest harm. This project refuses to reconstruct it."
    ),
)

RFS_CUTS: dict[str, PublishedResult] = {
    "primary": RFS_PRIMARY,
    "year3": RFS_3YEAR,
    "year5": RFS_5YEAR,
}

#: Endpoints this project will not reconstruct, and why. Checked at runtime.
REFUSED_RECONSTRUCTIONS: dict[str, str] = {
    "OS": (
        "Overall survival is not reconstructed: 7 deaths in each arm. A curve fitted "
        "to fourteen events would look like a finding and would be noise."
    ),
    "RFS:year3": (
        "The three-year analysis published no Kaplan-Meier figure with an at-risk "
        "table. Interpolating a curve between the primary and five-year "
        "reconstructions and labelling it 'three-year' would be fabrication."
    ),
}


class RefusedReconstruction(Exception):
    """This endpoint will not be reconstructed, on principle."""


def assert_reconstructible(endpoint: Endpoint, cut: str = "year5") -> None:
    """Refuse to reconstruct endpoints where a curve would mislead.

    Not every published number should be turned into a picture. Fourteen deaths
    drawn as two survival curves looks like a finding; it is noise. A three-year
    curve interpolated between two real reconstructions looks like data; it would
    be invention. Both refusals are enforced here rather than left to judgement.
    """
    for key in (endpoint, f"{endpoint}:{cut}"):
        if key in REFUSED_RECONSTRUCTIONS:
            raise RefusedReconstruction(REFUSED_RECONSTRUCTIONS[key])
