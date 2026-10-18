"""Ranking score.

Four components, each normalised to [0, 1], combined by weights that live in the
config file so they can be changed and argued with. A score that cannot be taken
apart is a score nobody can check, so every component is reported alongside the
total and the website lets the reader re-weight them.

What each component is asking:

``presentation``
    Will this fragment be displayed on the cell surface at all? Nothing else
    matters if the answer is no.
``agretopicity``
    Is the mutant displayed *better than* the normal version? The ratio of
    wild-type to mutant binding strength. A fragment presented equally well
    before the mutation teaches the immune system nothing new, and aiming at it
    risks aiming at healthy tissue.
``expression``
    Is the gene switched on in this tumour? A mutation in a silent gene produces
    no protein, so there is nothing to display.
``quality``
    Is the peptide awkward -- prone to oxidation, likely to be sugar-modified, or
    hard to manufacture?
"""

from __future__ import annotations

import math

from neoag.config import AgretopicityCfg, ExpressionCfg, GatesCfg, QualityCfg, ScoringCfg
from neoag.determinism import r
from neoag.models import ScoreComponents
from neoag.util.seq import N_GLYCOSYLATION, longest_homopolymer


def presentation_component(presentation_score: float) -> float:
    """Already a probability-like value in [0, 1]; used directly."""
    return r(min(1.0, max(0.0, presentation_score)))


def agretopicity_component(
    mut_affinity_nm: float, wt_affinity_nm: float | None, cfg: AgretopicityCfg
) -> tuple[float, float | None]:
    """Score how much better the mutant binds than the wild type.

    Returns ``(component, ratio)`` where ratio is ``wt_nM / mut_nM``. Lower nM
    means tighter binding, so a ratio above 1 means the mutation *improved*
    binding -- which is what makes a fragment newly visible.

    A missing wild-type measurement scores neutral rather than zero: absence of
    evidence is not evidence the mutation did nothing.
    """
    if wt_affinity_nm is None or mut_affinity_nm <= 0 or wt_affinity_nm <= 0:
        return r(cfg.missing_wt_score), None
    ratio = wt_affinity_nm / mut_affinity_nm
    low, high = cfg.log10_clip
    clipped = min(high, max(low, math.log10(ratio)))
    return r((clipped - low) / (high - low)), r(ratio)


def expression_component(percentile: float | None, cfg: ExpressionCfg) -> float:
    """Score expression by its rank within this tumour, not its absolute value.

    RSEM values are not comparable between genes, so a within-sample percentile
    is the honest summary.
    """
    if percentile is None:
        return r(cfg.missing_value_score)
    return r(min(1.0, max(0.0, percentile)))


def quality_component(peptide: str, cfg: QualityCfg) -> float:
    """Penalise awkward peptides. Starts at 1.0 and subtracts, floored at 0."""
    score = 1.0
    score -= cfg.cysteine_per_residue * peptide.count("C")
    if N_GLYCOSYLATION.search(peptide):
        score -= cfg.n_glycosylation_motif
    if longest_homopolymer(peptide) >= 4:
        score -= cfg.homopolymer_run_ge4
    return r(max(0.0, score))


def combine(
    presentation: float, agretopicity: float, expression: float, quality: float,
    weights: dict[str, float],
) -> ScoreComponents:
    """Weighted sum of the four components."""
    total = (
        weights["presentation"] * presentation
        + weights["agretopicity"] * agretopicity
        + weights["expression"] * expression
        + weights["quality"] * quality
    )
    return ScoreComponents(
        presentation=r(presentation),
        agretopicity=r(agretopicity),
        expression=r(expression),
        quality=r(quality),
        total=r(total),
    )


def passes_gates(
    presentation_percentile: float, affinity_nm: float, cfg: GatesCfg
) -> tuple[bool, str | None]:
    """Hard filters applied before ranking.

    A candidate that fails either filter is not merely low-ranked, it is not a
    candidate: these thresholds are the conventional boundary for "plausibly
    presented at all".
    """
    if presentation_percentile > cfg.max_presentation_percentile:
        return False, "gate_presentation_percentile"
    if affinity_nm > cfg.max_affinity_nm:
        return False, "gate_affinity"
    return True, None


def score_all(
    presentation_score: float,
    mut_affinity_nm: float,
    wt_affinity_nm: float | None,
    expression_percentile: float | None,
    peptide: str,
    cfg: ScoringCfg,
) -> tuple[ScoreComponents, float | None]:
    """Score one candidate, returning the components and the agretopicity ratio."""
    agreto, ratio = agretopicity_component(mut_affinity_nm, wt_affinity_nm, cfg.agretopicity)
    components = combine(
        presentation_component(presentation_score),
        agreto,
        expression_component(expression_percentile, cfg.expression),
        quality_component(peptide, cfg.quality),
        cfg.weights,
    )
    return components, ratio
