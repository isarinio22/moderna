"""Choosing the final set of epitopes.

Ranking alone is not enough. A single strongly-presented mutated residue produces
dozens of overlapping windows that all score well, and taking the top 34 by score
would fill the construct with 34 views of one target. If the tumour loses that
one mutation, the entire vaccine stops working.

So selection is greedy over the ranking subject to diversity caps: at most one
peptide per mutation, and a small number per gene. The result is 34 *independent*
targets rather than 34 restatements of the same one.
"""

from __future__ import annotations

from neoag.config import SelectionCfg
from neoag.determinism import ROUND
from neoag.models import ScoredEpitope


def stable_key(epitope: ScoredEpitope) -> tuple:
    """Total ordering with explicit tie-breaks.

    Floating-point reduction order can differ run to run, so scores are rounded
    before comparison and ties are broken by stable identifiers. Without this the
    selected set could change between runs on identical input.
    """
    return (
        -round(epitope.components.total, ROUND),
        epitope.gene,
        epitope.protein_position,
        epitope.length,
        epitope.mut_peptide,
        epitope.best_allele,
    )


def select(epitopes: list[ScoredEpitope], cfg: SelectionCfg) -> list[ScoredEpitope]:
    """Return every epitope with ``rank``, ``selected`` and ``exclusion_reason`` set."""
    ranked = sorted(epitopes, key=stable_key)

    per_mutation: dict[str, int] = {}
    per_gene: dict[str, int] = {}
    chosen = 0
    out: list[ScoredEpitope] = []

    for index, epitope in enumerate(ranked, start=1):
        reason = epitope.exclusion_reason  # gate failures arrive already marked
        selected = False

        if reason is not None:
            pass
        elif chosen >= cfg.max_epitopes:
            reason = "rank_cutoff"
        elif per_mutation.get(epitope.mutation_id, 0) >= cfg.max_per_mutation:
            reason = "mutation_cap"
        elif per_gene.get(epitope.gene, 0) >= cfg.max_per_gene:
            reason = "gene_cap"
        else:
            selected = True
            chosen += 1
            per_mutation[epitope.mutation_id] = per_mutation.get(epitope.mutation_id, 0) + 1
            per_gene[epitope.gene] = per_gene.get(epitope.gene, 0) + 1

        out.append(
            epitope.model_copy(update={"rank": index, "selected": selected, "exclusion_reason": reason})
        )

    return out
