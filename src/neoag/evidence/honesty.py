"""Plain-language explanations of what the statistics do and do not show.

These live in code rather than prose so the website, the slides and the post all
quote the same words, and so a test can assert that no figure caption overstates
what the trial found.

Each explainer carries a short plain version, a technical version, the caveats,
and its sources. The caveats are not optional decoration: for several of these,
the caveat *is* the point.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Explainer:
    """One concept, explained twice and qualified once."""

    key: str
    title: str
    plain: str
    technical: str
    caveats: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.plain.strip() or not self.technical.strip():
            raise ValueError(f"{self.key}: both plain and technical text are required")


#: Phrases this project will not use about this evidence, checked by a test.
BANNED_PHRASES: tuple[str, ...] = (
    "cure for cancer",
    "breakthrough cure",
    "cures cancer",
    "miracle",
    "saves lives",
    "proven to",
    "guarantees",
    "eliminates cancer",
    "game changer",
    "silver bullet",
)


EXPLAINERS: dict[str, Explainer] = {
    "hazard_ratio": Explainer(
        key="hazard_ratio",
        title="What a hazard ratio is",
        plain=(
            "A hazard ratio compares how quickly something is happening in two groups. "
            "A hazard ratio of 0.51 means that at any given moment, people who got the "
            "vaccine plus the antibody were recurring at about half the rate of people "
            "who got the antibody alone. It is a comparison of speeds, not a promise "
            "about any individual, and not a statement that half as many people "
            "recurred overall."
        ),
        technical=(
            "The ratio of instantaneous event rates between arms, estimated here by a "
            "Cox proportional hazards model. It is an average over the whole follow-up "
            "period and assumes the ratio is roughly constant throughout."
        ),
        caveats=(
            "It says nothing about absolute risk. A halving of a small risk is a small "
            "change in how many people are affected.",
            "It is an average over time. If the benefit grows or shrinks, one number "
            "hides that.",
        ),
        sources=("Cox DR, J R Stat Soc B 1972;34(2):187-220.",),
    ),
    "proportional_hazards": Explainer(
        key="proportional_hazards",
        title="The assumption behind the hazard ratio",
        plain=(
            "Summarising a whole trial with one hazard ratio assumes the gap between "
            "the two groups stays in roughly the same proportion over time. If the "
            "vaccine's benefit only appears after two years, or fades after four, a "
            "single number hides that shape."
        ),
        technical=(
            "Tested with Schoenfeld residuals. On this reconstruction the test does not "
            "detect a violation, but with about fifty events it has very little power "
            "to do so. Restricted mean survival time is reported alongside the hazard "
            "ratio because it requires no such assumption."
        ),
        caveats=(
            "Failing to detect a violation is not the same as showing there is none. "
            "With 51 events this test would miss most realistic departures.",
        ),
        sources=("Grambsch PM, Therneau TM, Biometrika 1994;81(3):515-526.",),
    ),
    "one_sided_alpha": Explainer(
        key="one_sided_alpha",
        title="The bar this trial set itself",
        plain=(
            "Before it started, the trial decided what would count as a positive "
            "result: a one-sided p-value below 0.10. That is a more forgiving "
            "threshold than the two-sided 0.05 most people have in mind. The headline "
            "p-value of 0.0266 cleared the bar the trial set. The same result stated "
            "the conventional way is p = 0.053, which would not have cleared the usual "
            "one. Both of those are true, and this project states both every time."
        ),
        technical=(
            "Designed for 80% power to detect a hazard ratio of 0.5 at an overall "
            "one-sided alpha of 0.10, requiring at least 40 recurrence events. The "
            "primary analysis occurred at 44 events."
        ),
        caveats=(
            "A one-sided test only looks for benefit. It cannot, by construction, "
            "find harm.",
            "Phase 2 trials often use looser thresholds deliberately, to decide "
            "whether a Phase 3 is worth running. That is a reasonable design choice, "
            "but it means the result is a reason to keep going, not a conclusion.",
        ),
        sources=("AACR 2023 abstract CT001.",),
    ),
    "nominal_p_values": Explainer(
        key="nominal_p_values",
        title="Why the later p-values are not what they look like",
        plain=(
            "The trial has been analysed three times as follow-up lengthened: the "
            "p-value went 0.0266, then 0.019, then 0.0075. It is tempting to read that "
            "as the evidence getting stronger. It is not that. Only the first analysis "
            "had a pre-agreed threshold. The later ones are extra looks at the same "
            "157 patients, with no correction for having looked repeatedly, and the "
            "presentation itself says no significance level was assigned to them."
        ),
        technical=(
            "The three-year and five-year analyses are nominal and descriptive, with "
            "no alpha allocated and no multiplicity adjustment. Repeated analyses of "
            "accumulating data inflate the chance of a small p-value even when nothing "
            "is happening."
        ),
        caveats=(
            "They are the same patients each time, not three independent findings.",
        ),
        sources=("ASCO 2026 abstract 9500 and oral presentation.",),
    ),
    "open_label": Explainer(
        key="open_label",
        title="Nobody was blinded",
        plain=(
            "Everyone in this trial knew which treatment they were getting, and so did "
            "their doctors. That matters more than it sounds, because the thing being "
            "measured is 'has the cancer come back?' -- which depends on when somebody "
            "orders a scan and how they read it. Expectation can shift both. The "
            "Phase 3 trial fixed this by giving everyone an injection, with half of "
            "them a placebo."
        ),
        technical=(
            "Open-label design with investigator-assessed recurrence-free survival as "
            "the primary endpoint, creating potential for ascertainment and assessment "
            "bias in the direction of the expected effect."
        ),
        caveats=(
            "Distant metastasis-free survival is somewhat more robust, being harder to "
            "miss or dispute, and it moved in the same direction.",
            "The size of any such bias is unknown and cannot be estimated from the "
            "published data.",
        ),
        sources=("Weber et al., Lancet 2024;403(10427):632-644.",),
    ),
    "small_sample": Explainer(
        key="small_sample",
        title="157 patients, 51 events",
        plain=(
            "The trial randomised 157 people, and after five years 51 of them had had "
            "a recurrence. Everything here rests on those 51 events. That is why the "
            "confidence interval is so wide: the data are compatible with the vaccine "
            "roughly tripling the time people stay cancer-free, and also with a much "
            "more modest benefit."
        ),
        technical=(
            "Hazard ratio 0.51 with a 95% confidence interval of 0.294 to 0.887. The "
            "interval excludes 1, but spans a wide range of effect sizes. Number needed "
            "to treat at five years is about 5, with an interval running past 70."
        ),
        caveats=(
            "Small positive trials systematically overstate effects, because a small "
            "trial only reaches significance when the observed effect is large.",
        ),
        sources=("ASCO 2026 abstract 9500.",),
    ),
    "rfs_is_not_survival": Explainer(
        key="rfs_is_not_survival",
        title="Staying cancer-free is not the same as living longer",
        plain=(
            "What this trial measured is how long people went without the cancer coming "
            "back. That is worth having on its own. But it is not the same as living "
            "longer, and this trial cannot tell us about that: there were 7 deaths in "
            "each group, 14 in total. You cannot learn much from 14 events. Anyone "
            "citing the survival numbers from this trial is overreaching."
        ),
        technical=(
            "Recurrence-free survival is the primary endpoint. Overall survival is "
            "exploratory, with a hazard ratio of 0.471 and a 95% interval from 0.165 "
            "to 1.345 -- an interval that includes both substantial benefit and modest "
            "harm. Recurrence-free survival has not been validated as a trial-level "
            "surrogate for overall survival in adjuvant melanoma."
        ),
        caveats=(
            "This project refuses to reconstruct the survival curve for exactly this "
            "reason: a curve drawn through 14 events would look like a finding.",
        ),
        sources=("ASCO 2026 abstract 9500.",),
    ),
    "number_needed_to_treat": Explainer(
        key="number_needed_to_treat",
        title="Number needed to treat, and why its interval looks strange",
        plain=(
            "Number needed to treat answers: how many people would have to get this "
            "treatment for one extra person to benefit? Here it is about 5 at five "
            "years. But the honest version includes the uncertainty, and that runs "
            "from about 3 to about 78. 'Somewhere between 3 and 78' is the real state "
            "of knowledge, and it is a much weaker claim than '5'."
        ),
        technical=(
            "The reciprocal of the absolute risk difference. When the risk difference's "
            "confidence interval includes zero, the reciprocal is not an interval at "
            "all but two rays extending to infinity, and must be reported as a number "
            "needed to benefit together with a number needed to harm. This project's "
            "result type cannot express a finite upper bound in that case."
        ),
        caveats=(
            "NNT depends entirely on the timepoint chosen. Quoting one without a "
            "timepoint is meaningless.",
        ),
        sources=("Altman DG, BMJ 1998;317(7168):1309-1312.",),
    ),
    "reconstruction_limits": Explainer(
        key="reconstruction_limits",
        title="What reconstructed data can and cannot tell you",
        plain=(
            "The patient-level data in this project was rebuilt from published summary "
            "tables. It reproduces the trial's published results closely, but nobody in "
            "it is a real person. It can be used to re-examine the headline numbers. It "
            "cannot be used to ask new questions, like whether the vaccine worked better "
            "in one subgroup."
        ),
        technical=(
            "Reconstructed from the published at-risk and cumulative-censoring columns, "
            "which determine the event counts in each interval exactly. The remaining "
            "freedom is where events fall within an interval, and the reported "
            "sensitivity analysis shows the hazard ratio moves by under 0.01 across "
            "reasonable choices. The published hazard ratio comes from a model "
            "stratified by disease stage; the reconstruction has no stage variable and "
            "is therefore unstratified, which is an irreducible source of difference."
        ),
        caveats=(
            "No subgroup, covariate or dose-response claim can be supported by "
            "reconstructed data.",
        ),
        sources=("Guyot P et al., BMC Med Res Methodol 2012;12:9.",),
    ),
    "phase_3": Explainer(
        key="phase_3",
        title="The real test is already finished, and not yet public",
        plain=(
            "A much larger Phase 3 trial of about 1,100 patients has already reported "
            "that it met its goals, in August 2026. That is the trial that actually "
            "settles this question: it is bigger, and everyone in it received an "
            "injection so nobody knew who got the vaccine. But no actual numbers from "
            "it have been published yet. 'It met its endpoints' is not a number, and "
            "this project does not pretend otherwise."
        ),
        technical=(
            "INTerpath-001 (NCT05933577): 1,137 patients randomised 2:1, "
            "double-blind against placebo plus pembrolizumab, met recurrence-free and "
            "distant metastasis-free survival at a pre-specified interim analysis. No "
            "hazard ratio, confidence interval or p-value is in the public domain as of "
            "2026-10-18."
        ),
        caveats=(
            "Nothing in this repository uses any Phase 3 efficacy figure, because none "
            "has been published.",
            "The product is not approved by any regulator anywhere.",
        ),
        sources=("Merck and Moderna joint release, 2026-08-19.",),
    ),
}


def verdict() -> str:
    """The project's one-paragraph bottom line, quoted verbatim everywhere."""
    return (
        "This is a genuinely promising result and it is not proof. A 157-patient, "
        "open-label Phase 2b trial found that adding a personalized vaccine to "
        "pembrolizumab left about 20 more people per 100 cancer-free at five years. "
        "The trial met the bar it set itself, which was a one-sided p below 0.10 -- a "
        "more forgiving threshold than the conventional one, which the same result "
        "would not have cleared. Nobody was blinded, the later analyses were not "
        "statistically protected, and with 14 deaths in total the trial says nothing "
        "about living longer. The biology is plausible and the direction is consistent "
        "across endpoints. The larger, blinded Phase 3 trial has reported that it met "
        "its goals, but has published no numbers. That trial, not this one, is the test."
    )


def check_text(text: str) -> list[str]:
    """Return any banned phrases appearing in ``text``. Used by a test over all copy."""
    lowered = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lowered]
