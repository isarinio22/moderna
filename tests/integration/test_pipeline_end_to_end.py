"""The whole pipeline, offline, with no model download.

Runs all six stages against the committed synthetic fixture using the stub
predictor. This is what makes the data flow testable in seconds and lets a fresh
clone verify the pipeline works before deciding whether to download 160 MB of
models.
"""

from __future__ import annotations

import pytest

from neoag.artifacts import canonical_dumps, read_json, write_json
from neoag.io.uniprot import parse_fasta
from neoag.models import MRNAConstruct, RankingResult
from neoag.pipeline import s1_fetch, s2_annotate, s3_peptides, s4_predict, s5_rank, s6_construct
from neoag.pipeline.predictors.base import load_predictor


@pytest.fixture(scope="module")
def pipeline():
    """Run every stage once and share the results across assertions."""
    from neoag.config import load_settings
    from neoag.paths import Paths

    paths = Paths()
    settings = load_settings([
        paths.root / "config" / "default.yaml",
        paths.root / "config" / "synthetic.yaml",
    ])
    proteome_fasta = parse_fasta((paths.fixtures / "synthetic_proteome.fasta").read_text())

    mutations = s1_fetch.run(settings, paths, None)
    annotations, proteome = s2_annotate.run(
        settings, paths, mutations, fixture_proteome=proteome_fasta
    )
    pairs = s3_peptides.run(settings, annotations, proteome)
    predictor = load_predictor("stub")
    predictions, _ = s4_predict.run(settings, pairs, predictor)
    ranking = s5_rank.run(settings, pairs, predictions, annotations)
    construct = s6_construct.run(settings, ranking, predictor)
    return {
        "settings": settings, "mutations": mutations, "annotations": annotations,
        "proteome": proteome, "pairs": pairs, "predictions": predictions,
        "ranking": ranking, "construct": construct,
    }


class TestStagesProduceSaneOutput:
    def test_fixture_loads_and_is_labelled_synthetic(self, pipeline):
        mutations = pipeline["mutations"]
        assert len(mutations.mutations) > 20
        assert mutations.provenance.origin == "synthetic"
        assert not mutations.provenance.is_real_measurement

    def test_every_mutation_validates_against_its_real_sequence(self, pipeline):
        """The fixture uses real proteins, so the reference check must pass cleanly."""
        annotations = pipeline["annotations"]
        assert len(annotations.annotated) == len(pipeline["mutations"].mutations)
        assert annotations.rejected == []
        assert annotations.mismatch_fraction == 0.0

    def test_peptides_span_their_mutations(self, pipeline):
        for pair in pipeline["pairs"]:
            assert pair.mut_peptide != pair.wt_peptide
            assert len(pair.mut_peptide) == pair.length
            assert 1 <= pair.mut_offset <= pair.length

    def test_predictions_cover_every_peptide_and_allele(self, pipeline):
        pairs, frame = pipeline["pairs"], pipeline["predictions"]
        expected = {p.mut_peptide for p in pairs} | {p.wt_peptide for p in pairs}
        assert set(frame["peptide"]) == expected
        assert set(frame["allele"]) == set(pipeline["settings"].hla.all_alleles)

    def test_selects_the_configured_number(self, pipeline):
        ranking = pipeline["ranking"]
        selected = [e for e in ranking.epitopes if e.selected]
        assert len(selected) == pipeline["settings"].selection.max_epitopes
        assert len(ranking.selected_ids) == len(selected)

    def test_selected_epitopes_are_independent_targets(self, pipeline):
        """The caps must hold: one per mutation, at most two per gene."""
        from collections import Counter

        selected = [e for e in pipeline["ranking"].epitopes if e.selected]
        cfg = pipeline["settings"].selection
        assert max(Counter(e.mutation_id for e in selected).values()) <= cfg.max_per_mutation
        assert max(Counter(e.gene for e in selected).values()) <= cfg.max_per_gene

    def test_every_rejected_candidate_has_a_reason(self, pipeline):
        for epitope in pipeline["ranking"].epitopes:
            assert epitope.selected or epitope.exclusion_reason

    def test_construct_is_marked_conceptual_everywhere(self, pipeline):
        construct = pipeline["construct"]
        assert construct.is_conceptual is True
        assert "CONCEPTUAL" in construct.disclaimer.upper()
        assert construct.constraints_satisfied["translation"] is True
        assert construct.constraints_satisfied["blocks_tile_sequence"] is True

    def test_construct_contains_every_selected_epitope(self, pipeline):
        construct, ranking = pipeline["construct"], pipeline["ranking"]
        assert set(construct.epitope_order) == set(ranking.selected_ids)
        assert len(construct.junction_report) == len(construct.epitope_order) - 1

    def test_stub_predictions_are_labelled_as_meaningless(self, pipeline):
        _, provenance = s4_predict.run(
            pipeline["settings"], pipeline["pairs"][:5], load_predictor("stub")
        )
        assert any("PLACEHOLDER" in note for note in provenance.notes)


class TestDeterminism:
    def test_two_runs_produce_identical_rankings(self, pipeline):
        repeat = s5_rank.run(
            pipeline["settings"], pipeline["pairs"], pipeline["predictions"],
            pipeline["annotations"],
        )
        first = pipeline["ranking"].model_dump(mode="json")
        second = repeat.model_dump(mode="json")
        first.pop("provenance"), second.pop("provenance")
        assert canonical_dumps(first) == canonical_dumps(second)

    def test_peptide_generation_is_deterministic(self, pipeline):
        repeat = s3_peptides.run(
            pipeline["settings"], pipeline["annotations"], pipeline["proteome"]
        )
        assert [p.peptide_pair_id for p in repeat] == [
            p.peptide_pair_id for p in pipeline["pairs"]
        ]


class TestArtifactRoundTrip:
    def test_ranking_survives_a_write_and_read(self, pipeline, tmp_path):
        path = tmp_path / "ranked.json"
        write_json(path, pipeline["ranking"], pipeline["ranking"].provenance)
        assert read_json(path, RankingResult) == pipeline["ranking"]

    def test_provenance_sidecar_is_written(self, pipeline, tmp_path):
        from neoag.artifacts import meta_path, read_provenance

        path = tmp_path / "construct.json"
        write_json(path, pipeline["construct"], pipeline["construct"].provenance)
        assert meta_path(path).exists()
        assert read_provenance(path).stage == "s6_construct"

    def test_construct_survives_a_write_and_read(self, pipeline, tmp_path):
        path = tmp_path / "c.json"
        write_json(path, pipeline["construct"])
        assert read_json(path, MRNAConstruct).full_sequence == pipeline["construct"].full_sequence

    def test_writes_are_atomic(self, tmp_path, pipeline):
        """No stray temporary files left behind."""
        path = tmp_path / "x.json"
        write_json(path, pipeline["ranking"])
        assert list(tmp_path.glob("*.tmp")) == []
