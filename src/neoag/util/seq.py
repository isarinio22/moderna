"""Sequence helpers: peptide windows, translation, composition.

The window arithmetic here is the heart of Part 1. Every off-by-one in this file
produces peptides that look plausible and are wrong, so each function states its
coordinate convention explicitly and the tests exercise both protein termini.

Convention: protein positions are **1-based and inclusive**, matching UniProt,
cBioPortal and every variant nomenclature. Python string indices are 0-based, so
residue at position ``p`` is ``seq[p - 1]``.
"""

from __future__ import annotations

import re

#: Residues that make a peptide unusable: stop, unknown, selenocysteine.
UNUSABLE_RESIDUES = frozenset("*XU")

#: N-linked glycosylation sequon, N-{P}-[ST]. A candidate carrying one may be
#: modified in ways that change presentation, so it is penalised, not excluded.
N_GLYCOSYLATION = re.compile(r"N[^P][ST]")

_CODON_TABLE: dict[str, str] = {}
_BASES = "TCAG"
_AAS = (
    "FFLLSSSSYY**CC*W"
    "LLLLPPPPHHQQRRRR"
    "IIIMTTTTNNKKSSRR"
    "VVVVAAAADDEEGGGG"
)
for _i, _b1 in enumerate(_BASES):
    for _j, _b2 in enumerate(_BASES):
        for _k, _b3 in enumerate(_BASES):
            _CODON_TABLE[_b1 + _b2 + _b3] = _AAS[_i * 16 + _j * 4 + _k]


def windows_spanning(protein_len: int, pos1: int, length: int) -> list[int]:
    """Return every 1-based start position of a ``length``-mer covering ``pos1``.

    A window starting at ``s`` covers positions ``s .. s + length - 1``. It is
    returned only if it both covers ``pos1`` and lies entirely within the protein.

    Returns an empty list when the protein is shorter than ``length``, or when the
    mutation sits too close to a terminus for any full-length window to fit --
    both are normal outcomes, not errors.

    >>> windows_spanning(100, 50, 9)[:3]
    [42, 43, 44]
    >>> windows_spanning(100, 1, 9)
    [1]
    >>> windows_spanning(7, 3, 9)
    []
    """
    if length <= 0 or protein_len <= 0 or not 1 <= pos1 <= protein_len:
        return []
    first = max(1, pos1 - length + 1)
    last = min(pos1, protein_len - length + 1)
    return list(range(first, last + 1)) if first <= last else []


def peptide_at(seq: str, start1: int, length: int) -> str:
    """Slice a peptide by 1-based inclusive start position."""
    return seq[start1 - 1 : start1 - 1 + length]


def is_usable_peptide(peptide: str) -> bool:
    """True when every residue is a translatable, standard amino acid."""
    return bool(peptide) and not (set(peptide) & UNUSABLE_RESIDUES)


def substitute(seq: str, pos1: int, new_aa: str) -> str:
    """Return ``seq`` with the residue at 1-based ``pos1`` replaced."""
    return seq[: pos1 - 1] + new_aa + seq[pos1:]


def translate(cds: str) -> str:
    """Translate a coding sequence. Trailing partial codons are ignored."""
    upper = cds.upper().replace("U", "T")
    return "".join(_CODON_TABLE.get(upper[i : i + 3], "X") for i in range(0, len(upper) - 2, 3))


def gc_content(dna: str) -> float:
    """Fraction of G or C bases. Returns 0.0 for an empty sequence."""
    if not dna:
        return 0.0
    return sum(1 for b in dna.upper() if b in "GC") / len(dna)


def longest_homopolymer(seq: str) -> int:
    """Length of the longest run of a single character."""
    best = run = 0
    prev = ""
    for ch in seq:
        run = run + 1 if ch == prev else 1
        prev = ch
        best = max(best, run)
    return best
