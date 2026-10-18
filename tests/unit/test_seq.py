"""Peptide window arithmetic.

Every off-by-one here produces peptides that look right and are wrong, so the
boundaries are tested explicitly rather than assumed.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from neoag.util.seq import (
    gc_content,
    is_usable_peptide,
    longest_homopolymer,
    peptide_at,
    substitute,
    translate,
    windows_spanning,
)

AA = "ACDEFGHIKLMNPQRSTVWY"


def test_interior_mutation_yields_one_window_per_offset():
    assert windows_spanning(100, 50, 9) == list(range(42, 51))
    assert len(windows_spanning(100, 50, 9)) == 9


def test_mutation_at_first_residue():
    """Only one window can both cover position 1 and fit inside the protein."""
    assert windows_spanning(100, 1, 9) == [1]
    assert windows_spanning(100, 1, 8) == [1]


def test_mutation_at_last_residue():
    assert windows_spanning(100, 100, 9) == [92]
    assert windows_spanning(100, 100, 11) == [90]


def test_protein_shorter_than_window_returns_empty():
    """Not an error: a 7-residue protein simply has no 9-mers."""
    assert windows_spanning(7, 3, 9) == []
    assert windows_spanning(9, 5, 9) == [1]


def test_position_outside_protein_returns_empty():
    assert windows_spanning(100, 0, 9) == []
    assert windows_spanning(100, 101, 9) == []


@given(
    protein_len=st.integers(min_value=1, max_value=200),
    length=st.integers(min_value=8, max_value=11),
    data=st.data(),
)
def test_every_window_covers_the_mutation_and_fits(protein_len, length, data):
    position = data.draw(st.integers(min_value=1, max_value=protein_len))
    for start in windows_spanning(protein_len, position, length):
        assert start >= 1
        assert start + length - 1 <= protein_len
        assert start <= position <= start + length - 1


@given(
    protein=st.text(alphabet=AA, min_size=12, max_size=80),
    length=st.integers(min_value=8, max_value=11),
    data=st.data(),
)
def test_mutant_and_wildtype_differ_at_exactly_one_position(protein, length, data):
    position = data.draw(st.integers(min_value=1, max_value=len(protein)))
    ref = protein[position - 1]
    alt = data.draw(st.sampled_from([a for a in AA if a != ref]))
    mutant = substitute(protein, position, alt)

    for start in windows_spanning(len(protein), position, length):
        wt_peptide = peptide_at(protein, start, length)
        mut_peptide = peptide_at(mutant, start, length)
        offset = position - start + 1
        assert len(mut_peptide) == len(wt_peptide) == length
        assert mut_peptide[offset - 1] == alt
        assert wt_peptide[offset - 1] == ref
        assert sum(a != b for a, b in zip(mut_peptide, wt_peptide, strict=True)) == 1


@pytest.mark.parametrize(
    "peptide,usable",
    [
        ("SIINFEKL", True), ("SIINFEK*", False), ("SIINFEKX", False),
        ("SIINFEKU", False), ("", False),
    ],
)
def test_unusable_residues_rejected(peptide, usable):
    assert is_usable_peptide(peptide) is usable


def test_translate_and_gc():
    assert translate("ATGGTGTAA") == "MV*"
    assert translate("ATGGTGTA") == "MV"  # trailing partial codon ignored
    assert gc_content("GCGC") == 1.0
    assert gc_content("ATAT") == 0.0
    assert gc_content("") == 0.0


def test_longest_homopolymer():
    assert longest_homopolymer("AAAA") == 4
    assert longest_homopolymer("ABAB") == 1
    assert longest_homopolymer("") == 0
