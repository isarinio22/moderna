"""Junction screening and epitope ordering.

Stitching epitopes end to end creates sequences that did not exist in the
tumour. A fragment spanning the seam between epitope 7 and epitope 8 can be
presented just like a real one -- and it corresponds to nothing, so any immune
response to it is wasted at best.

The linker reduces this, but does not eliminate it. So every seam is screened
and reported, and epitopes can be reordered to minimise the problem. Reporting
the junctions is as important as minimising them: it shows the reader a real
engineering trade-off rather than implying the construct is free of them.
"""

from __future__ import annotations

from neoag.models import JunctionPeptide, JunctionReport, ScoredEpitope
from neoag.pipeline.predictors.base import PresentationPredictor

STRONG_PERCENTILE = 2.0


def junction_peptides(left: str, linker: str, right: str, lengths: list[int]) -> list[str]:
    """Every k-mer spanning the seam, i.e. touching both epitopes."""
    joined = left + linker + right
    left_end = len(left)
    right_start = len(left) + len(linker)
    out: set[str] = set()
    for length in lengths:
        for start in range(len(joined) - length + 1):
            window = range(start, start + length)
            touches_left = any(i < left_end for i in window)
            touches_right = any(i >= right_start for i in window)
            if touches_left and touches_right:
                out.add(joined[start : start + length])
    return sorted(out)


def screen_junctions(
    order: list[str],
    epitopes: dict[str, ScoredEpitope],
    linker: str,
    lengths: list[int],
    alleles: list[str],
    predictor: PresentationPredictor,
) -> list[JunctionReport]:
    """Predict presentation for every seam peptide in the assembled order."""
    if len(order) < 2:
        return []

    seams = [(i, order[i], order[i + 1]) for i in range(len(order) - 1)]
    all_peptides: set[str] = set()
    per_seam: dict[int, list[str]] = {}
    for index, left_id, right_id in seams:
        peptides = junction_peptides(
            epitopes[left_id].mut_peptide, linker, epitopes[right_id].mut_peptide, lengths
        )
        per_seam[index] = peptides
        all_peptides.update(peptides)

    frame = predictor.predict(sorted(all_peptides), alleles)
    best: dict[str, tuple[str, float]] = {}
    for row in frame.itertuples(index=False):
        current = best.get(row.peptide)
        if current is None or row.presentation_percentile < current[1]:
            best[row.peptide] = (row.allele, float(row.presentation_percentile))

    reports: list[JunctionReport] = []
    for index, left_id, right_id in seams:
        entries = [
            JunctionPeptide(
                peptide=p, best_allele=best[p][0],
                presentation_percentile=round(best[p][1], 4),
            )
            for p in per_seam[index]
            if p in best
        ]
        entries.sort(key=lambda e: (e.presentation_percentile, e.peptide))
        reports.append(
            JunctionReport(
                junction_index=index,
                left_epitope_id=left_id,
                right_epitope_id=right_id,
                worst_percentile=(
                    round(entries[0].presentation_percentile, 4) if entries else 100.0
                ),
                n_strong_binders=sum(
                    1 for e in entries if e.presentation_percentile <= STRONG_PERCENTILE
                ),
                peptides=entries[:5],
            )
        )
    return reports


def order_epitopes(
    selected: list[ScoredEpitope],
    linker: str,
    lengths: list[int],
    alleles: list[str],
    predictor: PresentationPredictor,
    mode: str = "greedy",
) -> list[str]:
    """Choose an arrangement of epitopes.

    ``rank`` keeps score order and is free. ``greedy`` starts from the best
    epitope and repeatedly appends whichever remaining one creates the fewest
    strongly-presented seam peptides.
    """
    ids = [e.peptide_pair_id for e in selected]
    if mode == "rank" or len(ids) < 3:
        return ids

    by_id = {e.peptide_pair_id: e for e in selected}

    # Score every candidate seam in one prediction pass.
    pairs = [(a, b) for a in ids for b in ids if a != b]
    peptide_sets = {
        (a, b): junction_peptides(by_id[a].mut_peptide, linker, by_id[b].mut_peptide, lengths)
        for a, b in pairs
    }
    unique = sorted({p for peps in peptide_sets.values() for p in peps})
    frame = predictor.predict(unique, alleles)
    strongest: dict[str, float] = {}
    for row in frame.itertuples(index=False):
        value = float(row.presentation_percentile)
        if row.peptide not in strongest or value < strongest[row.peptide]:
            strongest[row.peptide] = value
    cost = {
        key: sum(1 for p in peps if strongest.get(p, 100.0) <= STRONG_PERCENTILE)
        for key, peps in peptide_sets.items()
    }

    remaining = set(ids[1:])
    order = [ids[0]]
    while remaining:
        current = order[-1]
        nxt = min(sorted(remaining), key=lambda cand: (cost.get((current, cand), 0), cand))
        order.append(nxt)
        remaining.remove(nxt)
    return order
