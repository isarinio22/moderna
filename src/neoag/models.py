"""Cross-stage data contracts.

Every model is frozen and forbids extra fields. That is deliberate: a typo in a
field name should be a loud validation error at a stage boundary, not a silent
``None`` that propagates into a figure.

Deliberate design choice: **rejected records are first-class**. Each stage carries
the things it threw away, with a machine-readable reason. A pipeline that
silently drops 40% of its input while looking like it worked is the single most
dangerous failure mode in bioinformatics, so here the discards are part of the
output and get published on the website.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from neoag import SCHEMA_VERSION
from neoag.provenance import Provenance


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DropRecord(_Frozen):
    """One input that did not make it through a stage, and why."""

    identifier: str
    stage: str
    reason: str
    detail: str = ""


# --------------------------------------------------------------------------- #
# Stage 1: raw variant calls
# --------------------------------------------------------------------------- #


class RawMutation(_Frozen):
    """A somatic variant exactly as cBioPortal reports it.

    Note ``protein_change`` has **no** ``p.`` prefix in the cBioPortal response
    (e.g. ``"V600E"``, not ``"p.V600E"``).
    """

    sample_id: str
    hugo_symbol: str
    entrez_gene_id: int
    chromosome: str
    start_position: int
    end_position: int
    reference_allele: str
    variant_allele: str
    protein_change: str
    mutation_type: str
    variant_type: str
    refseq_mrna_id: str | None = None
    #: Populated by sources that carry it directly (the synthetic fixture does).
    #: For cBioPortal records this is None and is resolved via Genome Nexus.
    uniprot_acc: str | None = None
    protein_pos_start: int | None = None
    protein_pos_end: int | None = None
    ncbi_build: str = "GRCh37"

    @property
    def mutation_id(self) -> str:
        """Stable identifier used as the join key by every later stage."""
        return (
            f"{self.hugo_symbol}:{self.chromosome}:{self.start_position}:"
            f"{self.reference_allele}>{self.variant_allele}"
        )

    @property
    def hgvs_g(self) -> str:
        """Genomic HGVS string, the input format Genome Nexus expects."""
        return (
            f"{self.chromosome}:g.{self.start_position}"
            f"{self.reference_allele}>{self.variant_allele}"
        )


class ExpressionValue(_Frozen):
    """RSEM expression for one gene in one sample. ``None`` means not measured."""

    entrez_gene_id: int
    hugo_symbol: str
    rsem: float | None = None


class MutationSet(_Frozen):
    """Output of stage 1."""

    schema_version: str = SCHEMA_VERSION
    study_id: str
    sample_id: str
    genome_build: str
    mutations: list[RawMutation]
    expression: list[ExpressionValue] = Field(default_factory=list)
    dropped: list[DropRecord] = Field(default_factory=list)
    provenance: Provenance


# --------------------------------------------------------------------------- #
# Stage 2: annotation and the reference-amino-acid check
# --------------------------------------------------------------------------- #

ValidationStatus = Literal[
    "ok",
    "mismatch",
    "no_sequence",
    "no_accession",
    "position_out_of_range",
    "sequence_too_short",
]


class RefAAValidation(_Frozen):
    """Result of checking the protein sequence against the variant call.

    ``status == "mismatch"`` is the signature of a genome-build error. It is the
    one failure this pipeline refuses to treat as a warning, because it produces
    plausible-looking wrong peptides rather than a crash.
    """

    status: ValidationStatus
    expected_aa: str
    observed_aa: str | None = None
    sequence_source: Literal["uniprot", "ensembl_grch37", "synthetic_fixture"] | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


class SequenceMeta(_Frozen):
    """Where one protein sequence came from."""

    accession: str
    source: Literal["uniprot", "ensembl_grch37", "synthetic_fixture"]
    url: str
    length: int
    sha: str


class ProteomeStore(_Frozen):
    """The protein sequences needed for this sample, keyed by accession."""

    sequences: dict[str, str] = Field(default_factory=dict)
    meta: dict[str, SequenceMeta] = Field(default_factory=dict)
    provenance: Provenance | None = None


class AnnotatedMutation(_Frozen):
    """A variant resolved to a protein position, with its validation verdict."""

    mutation_id: str
    raw: RawMutation
    transcript_id: str | None = None
    uniprot_acc: str | None = None
    hgvsp_short: str | None = None
    aa_ref: str
    aa_alt: str
    protein_position: int
    protein_length: int | None = None
    expression_rsem: float | None = None
    validation: RefAAValidation


class AnnotationSet(_Frozen):
    """Output of stage 2. ``annotated`` contains only records that validated."""

    schema_version: str = SCHEMA_VERSION
    sample_id: str
    annotated: list[AnnotatedMutation]
    rejected: list[AnnotatedMutation] = Field(default_factory=list)
    dropped: list[DropRecord] = Field(default_factory=list)
    provenance: Provenance

    @property
    def mismatch_fraction(self) -> float:
        """Share of resolved variants whose reference amino acid disagreed.

        A handful of mismatches is normal (stale annotations, isoform choice). A
        large share means the genome builds do not match and the run must abort.
        """
        considered = [
            m for m in self.annotated + self.rejected
            if m.validation.status != "no_accession"
        ]
        if not considered:
            return 0.0
        return sum(1 for m in considered if m.validation.status == "mismatch") / len(considered)


# --------------------------------------------------------------------------- #
# Stage 3: peptides
# --------------------------------------------------------------------------- #


class PeptidePair(_Frozen):
    """A mutant peptide and its matched wild-type counterpart.

    The pair is the unit of analysis, not the peptide: judging a candidate needs
    the contrast between mutant and wild-type binding, and that contrast is only
    meaningful when both are measured against the *same* HLA allele.
    """

    peptide_pair_id: str
    mutation_id: str
    gene: str
    uniprot_acc: str
    length: int
    peptide_start: int
    mut_offset: int
    mut_peptide: str
    wt_peptide: str
    protein_position: int
    expression_rsem: float | None = None
    flags: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Stage 5: scoring and selection
# --------------------------------------------------------------------------- #


class ScoreComponents(_Frozen):
    """The four parts of the ranking score, each in [0, 1], and their weighted sum."""

    presentation: float
    agretopicity: float
    expression: float
    quality: float
    total: float


class ScoredEpitope(_Frozen):
    """One candidate, scored and ranked."""

    peptide_pair_id: str
    mutation_id: str
    gene: str
    mut_peptide: str
    wt_peptide: str
    length: int
    protein_position: int
    mut_offset: int
    best_allele: str
    mut_affinity_nm: float
    wt_affinity_nm: float | None
    mut_presentation_score: float
    mut_presentation_percentile: float
    wt_presentation_score: float | None
    agretopicity_ratio: float | None
    expression_rsem: float | None
    expression_percentile: float | None
    components: ScoreComponents
    rank: int
    selected: bool
    exclusion_reason: str | None = None


class RankingResult(_Frozen):
    """Output of stage 5. Carries every candidate, not only the winners."""

    schema_version: str = SCHEMA_VERSION
    sample_id: str
    hla_alleles: list[str]
    epitopes: list[ScoredEpitope]
    selected_ids: list[str]
    weights: dict[str, float]
    gate_summary: dict[str, int] = Field(default_factory=dict)
    provenance: Provenance


# --------------------------------------------------------------------------- #
# Stage 6: the conceptual construct
# --------------------------------------------------------------------------- #

BlockKind = Literal["cap", "utr", "kozak", "signal", "epitope", "linker", "stop", "polya"]


class ConstructBlock(_Frozen):
    """One labelled region of the conceptual mRNA.

    ``start``/``end`` are 0-based half-open offsets into the full sequence. The
    5' cap is represented as a zero-length block: it is a chemical modification,
    not a nucleotide, and pretending otherwise would be wrong.
    """

    name: str
    kind: BlockKind
    start: int
    end: int
    sequence: str
    aa_sequence: str | None = None
    note: str = ""
    source_epitope_id: str | None = None


class JunctionPeptide(_Frozen):
    """A peptide formed across the seam between two epitopes."""

    peptide: str
    best_allele: str
    presentation_percentile: float


class JunctionReport(_Frozen):
    """Whether joining two epitopes created a novel presented peptide.

    Stitching epitopes together can create sequences that span the seam and are
    presented but correspond to nothing in the tumour. Reporting them is part of
    being honest about what this construct would and would not do.
    """

    junction_index: int
    left_epitope_id: str
    right_epitope_id: str
    worst_percentile: float
    n_strong_binders: int
    peptides: list[JunctionPeptide] = Field(default_factory=list)


class MRNAConstruct(_Frozen):
    """Output of stage 6. Conceptual and labelled as such at every level."""

    schema_version: str = SCHEMA_VERSION
    disclaimer: str
    is_conceptual: Literal[True] = True
    sample_id: str
    epitope_order: list[str]
    cds_aa: str
    full_sequence: str
    blocks: list[ConstructBlock]
    gc_content: float
    cds_length_nt: int
    total_length_nt: int
    codon_optimizer: Literal["dnachisel", "fallback_frequency_table"]
    constraints_satisfied: dict[str, bool] = Field(default_factory=dict)
    junction_report: list[JunctionReport] = Field(default_factory=list)
    provenance: Provenance
