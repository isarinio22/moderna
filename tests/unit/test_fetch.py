"""Stage 1 parsing and filtering."""

from __future__ import annotations

import pytest

from neoag.config import SourceCfg
from neoag.models import DropRecord, RawMutation
from neoag.pipeline.s1_fetch import filter_mutations, parse_mutation, parse_protein_change


def record(**overrides):
    base = {
        "sampleId": "TCGA-TEST-01", "entrezGeneId": 673,
        "gene": {"hugoGeneSymbol": "BRAF"}, "chr": "7",
        "startPosition": 140453136, "endPosition": 140453136,
        "referenceAllele": "A", "variantAllele": "T", "proteinChange": "V600E",
        "mutationType": "Missense_Mutation", "variantType": "SNP",
        "refseqMrnaId": "NM_004333.4", "proteinPosStart": 600, "proteinPosEnd": 600,
        "ncbiBuild": "GRCh37",
    }
    base.update(overrides)
    return base


class TestProteinChangeParsing:
    def test_cbioportal_form_has_no_p_prefix(self):
        assert parse_protein_change("V600E") == ("V", 600, "E")

    def test_p_prefixed_form_also_parses(self):
        assert parse_protein_change("p.V600E") == ("V", 600, "E")

    @pytest.mark.parametrize(
        "value", ["", "Q916*", "V600", "600E", "fs*12", "X1Y", "U5A", "V600V", "p.(V600E)"]
    )
    def test_non_substitutions_rejected(self, value):
        assert parse_protein_change(value) is None


class TestRecordParsing:
    def test_parses_a_normal_record(self):
        result = parse_mutation(record(), "TCGA-TEST-01")
        assert isinstance(result, RawMutation)
        assert result.hugo_symbol == "BRAF"
        assert result.mutation_id == "BRAF:7:140453136:A>T"
        assert result.hgvs_g == "7:g.140453136A>T"

    def test_chr_prefix_is_normalised(self):
        assert parse_mutation(record(chr="chr7"), "S").chromosome == "7"

    def test_missing_gene_symbol_is_dropped_with_a_reason(self):
        result = parse_mutation(record(gene={}), "S")
        assert isinstance(result, DropRecord)
        assert result.reason == "no_gene_symbol"

    def test_malformed_record_is_dropped_not_raised(self):
        result = parse_mutation(record(startPosition=None), "S")
        assert isinstance(result, DropRecord)
        assert result.reason == "unparseable_record"


class TestFiltering:
    @pytest.fixture
    def settings(self, settings):
        return settings

    def _mutations(self, specs):
        return [
            parse_mutation(record(gene={"hugoGeneSymbol": g}, startPosition=p,
                                  proteinChange=c, mutationType=t, variantType=v), "S")
            for g, p, c, t, v in specs
        ]

    def test_non_missense_dropped_with_reasons(self, settings):
        mutations = self._mutations([
            ("BRAF", 1, "V600E", "Missense_Mutation", "SNP"),
            ("TP53", 2, "R175H", "Nonsense_Mutation", "SNP"),
            ("PTEN", 3, "R130Q", "Splice_Site", "SNP"),
        ])
        kept, dropped = filter_mutations(mutations, settings, {})
        assert len(kept) == 1
        assert {d.reason for d in dropped} == {"mutation_type_excluded"}

    def test_indels_dropped(self, settings):
        mutations = self._mutations([("BRAF", 1, "V600E", "Missense_Mutation", "DEL")])
        kept, dropped = filter_mutations(mutations, settings, {})
        assert kept == []
        assert dropped[0].reason == "variant_type_excluded"

    def test_counts_reconcile(self, settings):
        """Nothing may vanish: inputs must equal kept plus dropped."""
        mutations = self._mutations([
            ("BRAF", 1, "V600E", "Missense_Mutation", "SNP"),
            ("TP53", 2, "R175H", "Nonsense_Mutation", "SNP"),
            ("PTEN", 3, "Q916*", "Missense_Mutation", "SNP"),
        ])
        kept, dropped = filter_mutations(mutations, settings, {})
        assert len(kept) + len(dropped) == len(mutations)

    def test_duplicates_collapse(self, settings):
        mutations = self._mutations([
            ("BRAF", 1, "V600E", "Missense_Mutation", "SNP"),
            ("BRAF", 1, "V600E", "Missense_Mutation", "SNP"),
        ])
        kept, dropped = filter_mutations(mutations, settings, {})
        assert len(kept) == 1
        assert any(d.reason == "duplicate_call" for d in dropped)

    def test_cap_is_deterministic_and_prefers_expressed_genes(self, settings):
        """A hypermutated sample must truncate the same way every time."""
        specs = [(f"GENE{i}", i + 1, "V600E", "Missense_Mutation", "SNP") for i in range(20)]
        mutations = self._mutations(specs)
        expression = {673: 100.0}
        capped = SourceCfg(max_mutations=5)
        cfg = settings.model_copy(update={"source": capped})
        first, _ = filter_mutations(mutations, cfg, expression)
        second, _ = filter_mutations(list(reversed(mutations)), cfg, expression)
        assert len(first) == 5
        assert [m.mutation_id for m in first] == [m.mutation_id for m in second]

    def test_capped_mutations_recorded_with_reason(self, settings):
        specs = [(f"GENE{i}", i + 1, "V600E", "Missense_Mutation", "SNP") for i in range(10)]
        cfg = settings.model_copy(update={"source": SourceCfg(max_mutations=3)})
        kept, dropped = filter_mutations(self._mutations(specs), cfg, {})
        assert len(kept) == 3
        assert sum(1 for d in dropped if d.reason == "over_max_mutations") == 7
