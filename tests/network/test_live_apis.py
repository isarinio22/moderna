"""Contract tests against the live public APIs.

Deselected by default (``-m network``). These exist to detect upstream drift
before a user hits it: if cBioPortal renames a field or UniProt changes a
sequence, these fail while the unit tests still pass.

The BRAF test is the canary that matters -- it asserts the real UniProt sequence
still has valine at position 600, which is the premise the whole peptide
pipeline rests on.
"""

from __future__ import annotations

import pytest

from neoag.io.cache import HttpCache
from neoag.io.cbioportal import CBioPortalClient
from neoag.io.ensembl_grch37 import Ensembl37Client
from neoag.io.genome_nexus import GenomeNexusClient, pick_transcript
from neoag.io.http import CachedHTTP
from neoag.io.uniprot import UniProtClient

pytestmark = pytest.mark.network

STUDY = "skcm_tcga_pan_can_atlas_2018"
SAMPLE = "TCGA-3N-A9WB-06"


@pytest.fixture(scope="module")
def http(tmp_path_factory):
    return CachedHTTP(HttpCache(tmp_path_factory.mktemp("cache")), "auto")


class TestUniProt:
    def test_braf_canonical_is_766_residues_with_valine_600(self, http):
        """The premise of every peptide this pipeline builds.

        If this fails, either UniProt changed its canonical BRAF or we are
        reading the wrong entry -- and in either case the protein positions in
        TCGA variant calls no longer line up.
        """
        sequences = UniProtClient(http).sequences(["P15056"])
        braf = sequences["P15056"]
        assert len(braf) == 766
        assert braf[599] == "V"

    def test_batch_fetch_returns_every_accession(self, http):
        wanted = ["P15056", "P01111", "P04637"]
        assert set(UniProtClient(http).sequences(wanted)) == set(wanted)


class TestEnsemblGRCh37:
    def test_grch37_braf_agrees_with_uniprot(self, http):
        """Two independent sources must agree, or our fallback is unsafe."""
        sequence = Ensembl37Client(http).protein_sequence("ENST00000288602")
        assert sequence is not None
        assert len(sequence) == 766
        assert sequence[599] == "V"


class TestCBioPortal:
    def test_study_is_present_and_grch37(self, http):
        study = CBioPortalClient(http).study(STUDY)
        assert study["referenceGenome"].lower() in ("hg19", "grch37")

    def test_mutation_response_still_has_every_field_we_read(self, http):
        """Contract test: the canary for a silent upstream rename."""
        records = CBioPortalClient(http).mutations(STUDY, [SAMPLE])
        assert records
        required = {
            "sampleId", "entrezGeneId", "gene", "chr", "startPosition", "endPosition",
            "referenceAllele", "variantAllele", "proteinChange", "mutationType",
            "variantType", "ncbiBuild",
        }
        assert required <= set(records[0])
        assert records[0]["ncbiBuild"] == "GRCh37"

    def test_protein_change_has_no_p_prefix(self, http):
        records = CBioPortalClient(http).mutations(STUDY, [SAMPLE])
        changes = [r["proteinChange"] for r in records if r.get("proteinChange")]
        assert changes
        assert not any(c.startswith("p.") for c in changes)

    def test_sample_is_in_the_sequenced_list(self, http):
        assert SAMPLE in CBioPortalClient(http).sequenced_sample_ids(STUDY)


class TestGenomeNexus:
    def test_braf_v600e_resolves_to_uniprot_and_grch37_numbering(self, http):
        annotations = GenomeNexusClient(http).annotate(["7:g.140453136A>T"])
        record = annotations["7:g.140453136A>T"]
        pick = pick_transcript(record, "V", 600)
        assert pick.uniprot_acc == "P15056"
        assert pick.aa_ref == "V"
        assert pick.protein_position == 600
