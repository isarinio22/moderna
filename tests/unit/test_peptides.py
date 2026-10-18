"""Peptide pair generation, flags and deduplication."""

from __future__ import annotations

from neoag.models import AnnotatedMutation, RawMutation, RefAAValidation
from neoag.pipeline.s3_peptides import dedupe, generate_pairs


def annotated(gene="BRAF", position=600, ref="V", alt="E", acc="P15056", start=1):
    raw = RawMutation(
        sample_id="T", hugo_symbol=gene, entrez_gene_id=1, chromosome="7",
        start_position=start, end_position=start, reference_allele="A", variant_allele="T",
        protein_change=f"{ref}{position}{alt}", mutation_type="Missense_Mutation",
        variant_type="SNP", uniprot_acc=acc,
    )
    return AnnotatedMutation(
        mutation_id=raw.mutation_id, raw=raw, uniprot_acc=acc, aa_ref=ref, aa_alt=alt,
        protein_position=position,
        validation=RefAAValidation(status="ok", expected_aa=ref, observed_aa=ref),
    )


PROTEIN = "MKVLAAGIVGPWSTIINFEKLNQYRHDCEMKVLAAGIVGPWSTIINFEKLNQYRHDCE"


def test_generates_every_length_for_an_interior_mutation():
    mutation = annotated(position=30, ref=PROTEIN[29], alt="W")
    pairs = generate_pairs(mutation, PROTEIN, [8, 9, 10, 11], set(), True)
    assert len(pairs) == 8 + 9 + 10 + 11


def test_mutant_residue_sits_at_the_recorded_offset():
    mutation = annotated(position=30, ref=PROTEIN[29], alt="W")
    for pair in generate_pairs(mutation, PROTEIN, [9], set(), True):
        assert pair.mut_peptide[pair.mut_offset - 1] == "W"
        assert pair.wt_peptide[pair.mut_offset - 1] == PROTEIN[29]


def test_terminal_mutations_are_flagged():
    first = annotated(position=1, ref=PROTEIN[0], alt="W")
    pairs = generate_pairs(first, PROTEIN, [9], set(), True)
    assert len(pairs) == 1
    assert "at_protein_start" in pairs[0].flags

    last = annotated(position=len(PROTEIN), ref=PROTEIN[-1], alt="W")
    pairs = generate_pairs(last, PROTEIN, [9], set(), True)
    assert "at_protein_end" in pairs[0].flags


def test_protein_shorter_than_window_yields_nothing():
    mutation = annotated(position=3, ref="K", alt="W")
    assert generate_pairs(mutation, "MKVLA", [9, 10, 11], set(), True) == []


def test_proximal_mutations_excluded_by_default():
    """Two mutations in one window: the true sequence depends on phasing we lack."""
    mutation = annotated(position=30, ref=PROTEIN[29], alt="W")
    without = generate_pairs(mutation, PROTEIN, [9], set(), True)
    with_neighbour = generate_pairs(mutation, PROTEIN, [9], {30, 32}, True)
    assert len(with_neighbour) < len(without)


def test_proximal_mutations_flagged_when_kept():
    mutation = annotated(position=30, ref=PROTEIN[29], alt="W")
    pairs = generate_pairs(mutation, PROTEIN, [9], {30, 32}, False)
    assert any("proximal_mutation" in p.flags for p in pairs)


def test_dedupe_collapses_identical_sequences():
    mutation = annotated(position=30, ref=PROTEIN[29], alt="W")
    pairs = generate_pairs(mutation, PROTEIN, [9], set(), True)
    duplicated = pairs + pairs
    assert len(dedupe(duplicated)) == len(dedupe(pairs))


def test_dedupe_is_order_independent():
    mutation = annotated(position=30, ref=PROTEIN[29], alt="W")
    pairs = generate_pairs(mutation, PROTEIN, [8, 9], set(), True)
    forward = [p.peptide_pair_id for p in dedupe(pairs)]
    backward = [p.peptide_pair_id for p in dedupe(list(reversed(pairs)))]
    assert forward == backward


def test_peptides_containing_stops_are_dropped():
    mutation = annotated(position=5, ref="A", alt="W")
    protein = "MKVL" + "A" + "*" + "GIVGPWSTIINFEKL"
    for pair in generate_pairs(mutation, protein, [9], set(), True):
        assert "*" not in pair.mut_peptide and "*" not in pair.wt_peptide
