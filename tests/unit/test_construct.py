"""Construct assembly, codon optimisation and junction screening."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from neoag.config import CodonCfg, ConstructCfg
from neoag.models import ScoreComponents, ScoredEpitope
from neoag.pipeline.construct.assemble import assemble, build_protein, to_fasta
from neoag.pipeline.construct.codon import fallback_best_codon, optimize_cds
from neoag.pipeline.construct.junctions import junction_peptides
from neoag.util.seq import translate

AA = "ACDEFGHIKLMNPQRSTVWY"
DISCLAIMER = "CONCEPTUAL AND EDUCATIONAL ONLY. Not a manufacturable sequence."


def epitope(pair_id, peptide, gene="BRAF"):
    return ScoredEpitope(
        peptide_pair_id=pair_id, mutation_id=pair_id, gene=gene, mut_peptide=peptide,
        wt_peptide=peptide, length=len(peptide), protein_position=1, mut_offset=1,
        best_allele="HLA-A*02:01", mut_affinity_nm=10.0, wt_affinity_nm=1000.0,
        mut_presentation_score=0.9, mut_presentation_percentile=0.1,
        wt_presentation_score=0.1, agretopicity_ratio=100.0, expression_rsem=10.0,
        expression_percentile=0.9,
        components=ScoreComponents(presentation=0.9, agretopicity=1.0, expression=0.9,
                                   quality=1.0, total=0.9),
        rank=1, selected=True,
    )


class TestCodonOptimisation:
    @given(aa=st.text(alphabet=AA, min_size=10, max_size=60))
    @hyp_settings(max_examples=25, deadline=None)
    def test_fallback_always_translates_back(self, aa):
        assert translate(fallback_best_codon(aa)) == aa

    def test_optimised_sequence_translates_back(self):
        aa = "MKVLAAGIVGPGPGSIINFEKLGPGPGNLVPMVATVKVLELNTLV"
        result = optimize_cds(aa, CodonCfg())
        assert translate(result.cds) == aa

    def test_result_records_which_path_ran(self):
        result = optimize_cds("MKVLAAGIVG", CodonCfg())
        assert result.optimizer in ("dnachisel", "fallback_frequency_table")
        assert "translation" in result.constraints_satisfied

    def test_same_seed_gives_identical_sequence(self):
        aa = "MKVLAAGIVGPGPGSIINFEKL"
        assert optimize_cds(aa, CodonCfg(), seed=7).cds == optimize_cds(aa, CodonCfg(), seed=7).cds

    def test_unsatisfiable_constraint_is_reported_not_hidden(self):
        """An impossible GC band must surface as a failed constraint, not a wrong sequence."""
        aa = "GPGPGPGPGPGPGPGPGPGP"  # every G and P codon is GC-rich
        result = optimize_cds(aa, CodonCfg(gc_target=[0.0, 0.10], gc_window=20))
        assert translate(result.cds) == aa
        assert result.constraints_satisfied["gc_content"] is False


class TestJunctions:
    def test_peptides_touch_both_sides(self):
        peptides = junction_peptides("SIINFEKL", "GPGPG", "NLVPMVATV", [9])
        assert peptides
        assert all(p != "GPGPG" for p in peptides)

    def test_no_seam_means_no_junction_peptides(self):
        """With nothing on the right there is no seam to screen."""
        assert junction_peptides("SIINFEKL", "GPGPG", "", [9]) == []

    def test_longer_windows_give_more_peptides(self):
        nine = junction_peptides("SIINFEKL", "GPGPG", "NLVPMVATV", [9])
        both = junction_peptides("SIINFEKL", "GPGPG", "NLVPMVATV", [9, 10])
        assert len(both) > len(nine)


class TestAssembly:
    @pytest.fixture
    def assembled(self):
        epitopes = {f"e{i}": epitope(f"e{i}", p) for i, p in
                    enumerate(["SIINFEKL", "NLVPMVATV", "GILGFVFTL"])}
        order = ["e0", "e1", "e2"]
        return assemble(order, epitopes, ConstructCfg(disclaimer=DISCLAIMER), 1337, [])

    def test_blocks_tile_the_sequence_exactly(self, assembled):
        full, blocks, _, _, constraints = assembled
        assert constraints["blocks_tile_sequence"] is True
        cursor = 0
        for block in blocks:
            assert block.start == cursor
            cursor = block.end
        assert cursor == len(full)

    def test_cap_is_a_zero_length_block(self, assembled):
        """The cap is a chemical modification, not a base. Inventing letters would lie."""
        _, blocks, _, _, _ = assembled
        cap = next(b for b in blocks if b.kind == "cap")
        assert cap.sequence == ""
        assert cap.start == cap.end
        assert "modification" in cap.note

    def test_every_epitope_appears_as_a_block(self, assembled):
        _, blocks, _, _, _ = assembled
        assert sum(1 for b in blocks if b.kind == "epitope") == 3

    def test_linkers_sit_between_epitopes_only(self, assembled):
        _, blocks, _, _, _ = assembled
        assert sum(1 for b in blocks if b.kind == "linker") == 2

    def test_coding_blocks_translate_to_the_intended_protein(self, assembled):
        _, blocks, cds_aa, _, _ = assembled
        coding = "".join(b.sequence for b in blocks if b.kind in ("epitope", "linker"))
        assert translate(coding) == cds_aa

    def test_utrs_are_real_sequences_with_provenance(self, assembled):
        """Real globin UTRs, each labelled with the transcript it came from."""
        _, blocks, _, _, _ = assembled
        utrs = [b for b in blocks if b.kind == "utr"]
        assert len(utrs) == 2
        for block in utrs:
            assert "ENST" in block.note
            assert "GRCh37" in block.note
            assert set(block.sequence) <= set("ACGT")

    def test_three_prime_utr_labels_the_polyadenylation_signal(self, assembled):
        """The poly-A tail is placed, not merely appended -- AATAAA is where."""
        _, blocks, _, _, _ = assembled
        tail_utr = [b for b in blocks if b.kind == "utr"][-1]
        assert "AATAAA" in tail_utr.sequence
        assert "polyadenylation signal" in tail_utr.note


def test_build_protein_joins_with_linkers():
    epitopes = {"a": epitope("a", "SIINFEKL"), "b": epitope("b", "NLVPMVATV")}
    assert build_protein(["a", "b"], epitopes, "GPGPG") == "SIINFEKLGPGPGNLVPMVATV"


def test_fasta_header_carries_the_disclaimer():
    fasta = to_fasta("S1", "ACGT" * 30, DISCLAIMER)
    assert fasta.startswith(">S1_conceptual_construct")
    assert "CONCEPTUAL" in fasta.splitlines()[0]
