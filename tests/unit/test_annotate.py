"""The reference-amino-acid guard.

This is the most important test file in the repository. The failure it guards
against is not a crash -- it is a run that completes successfully and produces
entirely wrong peptides, because the protein sequence used different numbering
than the variant call.
"""

from __future__ import annotations

import pytest

from neoag.errors import ForbiddenHostError
from neoag.io.http import FORBIDDEN_HOSTS, check_host
from neoag.pipeline.s2_annotate import validate_reference


class TestBrafRegression:
    """BRAF V600E across genome builds -- the canonical silent-corruption case.

    GRCh37 and UniProt give a 766-residue BRAF with valine at 600. The current
    GRCh38 Ensembl model gives 806 residues with threonine at 600. TCGA variant
    calls use GRCh37 numbering, so resolving against GRCh38 shifts every protein
    position and produces plausible, wrong peptides.
    """

    def test_correct_build_validates(self, braf_grch37):
        result = validate_reference(braf_grch37, 600, "V", "uniprot")
        assert result.ok
        assert result.observed_aa == "V"

    def test_wrong_build_is_rejected_not_warned(self, braf_grch38):
        """The whole point: a build mismatch must stop the record, not annotate it."""
        result = validate_reference(braf_grch38, 600, "V", "uniprot")
        assert not result.ok
        assert result.status == "mismatch"
        assert result.observed_aa == "T"
        assert "genome-build" in result.message

    def test_the_two_builds_really_do_differ(self, braf_grch37, braf_grch38):
        """Guards the fixtures themselves, so this test cannot pass vacuously."""
        assert len(braf_grch37) == 766
        assert len(braf_grch38) == 806
        assert braf_grch37[599] == "V"
        assert braf_grch38[599] == "T"


def test_position_beyond_protein_end():
    result = validate_reference("MVK", 50, "V")
    assert result.status == "position_out_of_range"
    assert not result.ok


def test_missing_sequence():
    result = validate_reference(None, 600, "V")
    assert result.status == "no_sequence"
    assert not result.ok


def test_empty_sequence_is_not_silently_ok():
    assert validate_reference("", 1, "M").status == "no_sequence"


@pytest.mark.parametrize("position", [1, 2])
def test_first_residues_validate(position):
    assert validate_reference("MVKL", position, "MV"[position - 1]).ok


class TestForbiddenHost:
    """The wrong genome build is blocked at the transport layer, not by convention."""

    def test_grch38_ensembl_is_blocked(self):
        with pytest.raises(ForbiddenHostError, match="GRCh38"):
            check_host("https://rest.ensembl.org/sequence/id/ENST00000288602")

    def test_grch37_ensembl_is_allowed(self):
        check_host("https://grch37.rest.ensembl.org/sequence/id/ENST00000288602")

    def test_other_hosts_allowed(self):
        check_host("https://rest.uniprot.org/uniprotkb/P15056.fasta")
        check_host("https://www.cbioportal.org/api/studies")

    def test_block_explains_why(self):
        assert "BRAF" in FORBIDDEN_HOSTS["rest.ensembl.org"]
