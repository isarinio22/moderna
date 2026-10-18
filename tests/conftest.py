"""Shared fixtures.

The important one is ``_no_network``: it makes any accidental live request in a
test that is not explicitly marked ``network`` fail loudly. Without it, a test
can quietly depend on the internet and then fail for someone else, or worse,
pass for the wrong reason.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from neoag.config import Settings, load_settings
from neoag.models import AnnotatedMutation, RawMutation, RefAAValidation
from neoag.paths import Paths

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_network(request, monkeypatch):
    """Block sockets unless the test is marked ``network``."""
    if request.node.get_closest_marker("network"):
        return

    def blocked(*args, **kwargs):
        raise AssertionError(
            "this test tried to open a network connection. Mark it with "
            "@pytest.mark.network, or use a fixture instead."
        )

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def settings() -> Settings:
    return load_settings([REPO / "config" / "default.yaml"])


@pytest.fixture
def synthetic_settings() -> Settings:
    return load_settings([REPO / "config" / "default.yaml", REPO / "config" / "synthetic.yaml"])


@pytest.fixture
def paths() -> Paths:
    return Paths(REPO)


@pytest.fixture
def braf_mutation() -> AnnotatedMutation:
    """BRAF V600E, the canonical test case for genome-build confusion."""
    raw = RawMutation(
        sample_id="TEST", hugo_symbol="BRAF", entrez_gene_id=673, chromosome="7",
        start_position=140453136, end_position=140453136, reference_allele="A",
        variant_allele="T", protein_change="V600E", mutation_type="Missense_Mutation",
        variant_type="SNP", uniprot_acc="P15056",
    )
    return AnnotatedMutation(
        mutation_id=raw.mutation_id, raw=raw, uniprot_acc="P15056", aa_ref="V", aa_alt="E",
        protein_position=600, protein_length=766,
        validation=RefAAValidation(status="ok", expected_aa="V", observed_aa="V"),
    )


@pytest.fixture
def braf_grch37() -> str:
    """766-residue protein with valine at 600, as GRCh37 and UniProt have it."""
    return "M" * 599 + "V" + "AGSTLKRHE" * 18 + "AAAA"


@pytest.fixture
def braf_grch38() -> str:
    """806-residue protein with threonine at 600, as current GRCh38 Ensembl has it."""
    return "M" * 599 + "T" + "AGSTLKRHE" * 22 + "AAAAAAAA"
