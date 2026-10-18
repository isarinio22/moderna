"""Codon optimisation, with a guaranteed offline fallback.

Most amino acids can be written with several different codons, and human cells
read some faster than others. Choosing the preferred codons is one of the levers
that makes a therapeutic mRNA produce more protein.

DnaChisel does this well but is a constraint solver and can be slow or fail to
converge. Since this is the last stage of the pipeline, a hang here would waste
the whole run -- so there is always a fallback that simply picks the most
frequent human codon for each residue. It is less sophisticated, it always
succeeds, and which path ran is recorded in the output.
"""

from __future__ import annotations

from dataclasses import dataclass

from neoag.config import CodonCfg

#: Most-frequent human codon per amino acid (Kazusa human codon usage).
#: Used by the fallback path; the primary path reads the table from
#: ``python_codon_tables`` via DnaChisel.
BEST_HUMAN_CODON: dict[str, str] = {
    "A": "GCC", "R": "AGG", "N": "AAC", "D": "GAC", "C": "TGC", "Q": "CAG", "E": "GAG",
    "G": "GGC", "H": "CAC", "I": "ATC", "L": "CTG", "K": "AAG", "M": "ATG", "F": "TTC",
    "P": "CCC", "S": "AGC", "T": "ACC", "W": "TGG", "Y": "TAC", "V": "GTG",
}


@dataclass(frozen=True)
class CodonResult:
    cds: str
    optimizer: str
    constraints_satisfied: dict[str, bool]
    message: str = ""


def fallback_best_codon(aa_sequence: str) -> str:
    """Translate protein to DNA using the most frequent human codon for each residue."""
    return "".join(BEST_HUMAN_CODON.get(aa, "NNN") for aa in aa_sequence)


def optimize_cds(aa_sequence: str, cfg: CodonCfg, seed: int = 1337) -> CodonResult:
    """Codon-optimise a protein sequence, falling back if the solver cannot.

    The invariant that matters, on every path: the result must translate back to
    exactly the input protein. Verified before returning.
    """
    from neoag.util.seq import gc_content, translate

    result = _try_dnachisel(aa_sequence, cfg, seed)
    if result is None:
        cds = fallback_best_codon(aa_sequence)
        gc = gc_content(cds)
        result = CodonResult(
            cds=cds,
            optimizer="fallback_frequency_table",
            constraints_satisfied={
                "translation": translate(cds) == aa_sequence,
                "gc_content": cfg.gc_target[0] <= gc <= cfg.gc_target[1],
                "avoid_patterns": all(p not in cds for p in cfg.avoid_patterns),
            },
            message="DnaChisel unavailable or did not converge; used frequency table.",
        )

    if translate(result.cds) != aa_sequence:
        raise AssertionError(
            "codon optimisation changed the protein. This is a bug, not a constraint failure."
        )
    return result


def _try_dnachisel(aa_sequence: str, cfg: CodonCfg, seed: int) -> CodonResult | None:
    try:
        import random

        import numpy as np
        from dnachisel import (
            AvoidPattern,
            CodonOptimize,
            DnaOptimizationProblem,
            EnforceGCContent,
            EnforceTranslation,
            reverse_translate,
        )
    except ImportError:
        return None

    from neoag.util.seq import gc_content, translate

    random.seed(seed)
    np.random.seed(seed)

    try:
        start = reverse_translate(aa_sequence)
        problem = DnaOptimizationProblem(
            sequence=start,
            constraints=[
                EnforceTranslation(),
                EnforceGCContent(mini=cfg.gc_target[0], maxi=cfg.gc_target[1], window=cfg.gc_window),
                *[AvoidPattern(p) for p in cfg.avoid_patterns],
            ],
            objectives=[CodonOptimize(species=cfg.species, method=cfg.method)],
            logger=None,
        )
        # The default random search is too small for a ~1.5 kb construct whose
        # GPGPG linkers are locally GC-rich by construction.
        problem.max_random_iters = 20000
        problem.resolve_constraints(final_check=False)
        problem.optimize()
        cds = str(problem.sequence)
    except Exception:  # noqa: BLE001 - solver failure is expected; caller falls back
        return None

    if translate(cds) != aa_sequence:
        return None

    gc = gc_content(cds)
    return CodonResult(
        cds=cds,
        optimizer="dnachisel",
        constraints_satisfied={
            "translation": True,
            "gc_content": cfg.gc_target[0] <= gc <= cfg.gc_target[1],
            "avoid_patterns": all(p not in cds for p in cfg.avoid_patterns),
        },
    )
