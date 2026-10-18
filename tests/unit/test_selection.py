"""Diversity-constrained selection.

Ranking alone would fill the construct with many views of a single strong
mutation. These tests pin the caps that prevent it.
"""

from __future__ import annotations

from neoag.config import SelectionCfg
from neoag.models import ScoreComponents, ScoredEpitope
from neoag.pipeline.selection import select


def make(pair_id, mutation_id, gene, total, position=100, peptide="SIINFEKL", allele="HLA-A*02:01"):
    return ScoredEpitope(
        peptide_pair_id=pair_id, mutation_id=mutation_id, gene=gene,
        mut_peptide=peptide, wt_peptide=peptide, length=len(peptide),
        protein_position=position, mut_offset=1, best_allele=allele,
        mut_affinity_nm=10.0, wt_affinity_nm=1000.0, mut_presentation_score=0.9,
        mut_presentation_percentile=0.5, wt_presentation_score=0.1,
        agretopicity_ratio=100.0, expression_rsem=100.0, expression_percentile=0.9,
        components=ScoreComponents(presentation=0.9, agretopicity=1.0, expression=0.9,
                                   quality=1.0, total=total),
        rank=0, selected=False,
    )


def test_one_peptide_per_mutation_by_default():
    """38 overlapping windows of one hot residue must collapse to its best peptide."""
    epitopes = [make(f"m|{i}|9", "MUT1", "BRAF", 0.9 - i * 0.001, peptide=f"SIINFEK{chr(65+i%20)}")
                for i in range(38)]
    result = select(epitopes, SelectionCfg())
    assert sum(e.selected for e in result) == 1
    assert {e.exclusion_reason for e in result if not e.selected} == {"mutation_cap"}


def test_gene_cap_limits_a_dominant_gene():
    epitopes = [make(f"p{i}", f"MUT{i}", "BRAF", 0.9 - i * 0.01) for i in range(10)]
    result = select(epitopes, SelectionCfg(max_per_gene=2))
    assert sum(e.selected for e in result) == 2
    assert any(e.exclusion_reason == "gene_cap" for e in result)


def test_selects_up_to_the_cap():
    epitopes = [make(f"p{i}", f"MUT{i}", f"GENE{i}", 0.9 - i * 0.001) for i in range(50)]
    result = select(epitopes, SelectionCfg(max_epitopes=34))
    assert sum(e.selected for e in result) == 34
    assert any(e.exclusion_reason == "rank_cutoff" for e in result)


def test_fewer_candidates_than_cap_selects_all():
    epitopes = [make(f"p{i}", f"MUT{i}", f"GENE{i}", 0.9) for i in range(10)]
    result = select(epitopes, SelectionCfg(max_epitopes=34))
    assert sum(e.selected for e in result) == 10


def test_empty_input_does_not_crash():
    assert select([], SelectionCfg()) == []


def test_gated_candidates_keep_their_reason_and_are_never_selected():
    epitopes = [make(f"p{i}", f"MUT{i}", f"GENE{i}", 0.9) for i in range(5)]
    epitopes[0] = epitopes[0].model_copy(update={"exclusion_reason": "gate_affinity"})
    result = select(epitopes, SelectionCfg())
    gated = next(e for e in result if e.peptide_pair_id == "p0")
    assert not gated.selected
    assert gated.exclusion_reason == "gate_affinity"


def test_selection_is_order_independent():
    """Identical scores must resolve identically however the input is shuffled."""
    import random

    epitopes = [make(f"p{i}", f"MUT{i}", f"GENE{i % 7}", 0.5) for i in range(40)]
    baseline = {e.peptide_pair_id for e in select(epitopes, SelectionCfg()) if e.selected}
    for seed in range(20):
        shuffled = epitopes[:]
        random.Random(seed).shuffle(shuffled)
        chosen = {e.peptide_pair_id for e in select(shuffled, SelectionCfg()) if e.selected}
        assert chosen == baseline


def test_rank_is_assigned_densely_over_all_candidates():
    epitopes = [make(f"p{i}", f"MUT{i}", f"GENE{i}", 0.9 - i * 0.01) for i in range(5)]
    result = select(epitopes, SelectionCfg())
    assert [e.rank for e in result] == [1, 2, 3, 4, 5]
