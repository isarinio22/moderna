"""Configuration: YAML in, validated frozen settings out.

Weights and thresholds live in YAML so they can be changed without touching
Python, and are validated into pydantic models so a typo fails at startup rather
than silently becoming a ``KeyError`` three stages later.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from neoag.errors import ConfigError
from neoag.util.hashing import digest

OfflineMode = Literal["auto", "offline", "refresh"]


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class RunCfg(_Cfg):
    seed: int = 1337
    offline_mode: OfflineMode = "auto"
    predictor: Literal["mhcflurry", "stub"] = "mhcflurry"
    #: Abort if more than this share of variants fail the reference-amino-acid
    #: check. A few failures are stale annotations; many mean the genome builds
    #: do not match and every peptide downstream would be wrong.
    max_mismatch_fraction: float = 0.25


class SourceCfg(_Cfg):
    study_id: str = "skcm_tcga_pan_can_atlas_2018"
    sample_id: str = "TCGA-3N-A9WB-06"
    genome_build: str = "GRCh37"
    use_synthetic: bool = False
    #: Cap on variants carried forward. Melanoma is the highest mutation-burden
    #: tumour type and a hypermutated sample would blow the runtime budget.
    max_mutations: int = 150
    mutation_types: list[str] = Field(default_factory=lambda: ["Missense_Mutation"])
    variant_types: list[str] = Field(default_factory=lambda: ["SNP"])


class HlaCfg(_Cfg):
    """HLA alleles to predict against.

    ASSUMPTION, NOT DATA: cBioPortal publishes no HLA type for TCGA samples, and
    which peptides a person can present depends entirely on their HLA type. These
    panels are illustrative sets of commonly observed class I alleles. Real
    neoantigen selection uses the patient's own sequenced HLA type.
    """

    primary_panel: str = "common_european"
    panels: dict[str, list[str]]
    assumption_note: str

    @model_validator(mode="after")
    def _primary_exists(self) -> HlaCfg:
        if self.primary_panel not in self.panels:
            raise ValueError(f"primary_panel {self.primary_panel!r} is not in panels")
        if not self.assumption_note.strip():
            raise ValueError("assumption_note must be non-empty; the HLA set is an assumption")
        return self

    @property
    def primary_alleles(self) -> list[str]:
        return list(self.panels[self.primary_panel])

    @property
    def all_alleles(self) -> list[str]:
        return sorted({a for alleles in self.panels.values() for a in alleles})


class PeptideCfg(_Cfg):
    lengths: list[int] = Field(default_factory=lambda: [8, 9, 10, 11])
    #: Exclude windows containing a second somatic mutation: their true sequence
    #: depends on whether the two variants are on the same chromosome copy, which
    #: this data cannot tell us.
    exclude_proximal_mutations: bool = True


class AgretopicityCfg(_Cfg):
    log10_clip: list[float] = Field(default_factory=lambda: [-1.0, 2.0])
    missing_wt_score: float = 0.5


class ExpressionCfg(_Cfg):
    missing_value_score: float = 0.5


class QualityCfg(_Cfg):
    cysteine_per_residue: float = 0.15
    n_glycosylation_motif: float = 0.10
    homopolymer_run_ge4: float = 0.10


class GatesCfg(_Cfg):
    max_presentation_percentile: float = 2.0
    max_affinity_nm: float = 500.0


class ScoringCfg(_Cfg):
    weights: dict[str, float]
    agretopicity: AgretopicityCfg = AgretopicityCfg()
    expression: ExpressionCfg = ExpressionCfg()
    quality: QualityCfg = QualityCfg()
    gates: GatesCfg = GatesCfg()

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> ScoringCfg:
        expected = {"presentation", "agretopicity", "expression", "quality"}
        if set(self.weights) != expected:
            raise ValueError(f"scoring.weights must have exactly the keys {sorted(expected)}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"scoring.weights must sum to 1.0, got {total}")
        return self


class SelectionCfg(_Cfg):
    #: The real vaccine encodes up to 34 neoantigens.
    max_epitopes: int = 34
    #: One peptide per mutation: 34 overlapping windows of one hot residue would
    #: be 34 views of a single target, not 34 targets.
    max_per_mutation: int = 1
    max_per_gene: int = 2


class CodonCfg(_Cfg):
    species: str = "h_sapiens"
    table: str = "h_sapiens_9606"
    method: str = "use_best_codon"
    gc_target: list[float] = Field(default_factory=lambda: [0.45, 0.60])
    gc_window: int = 50
    avoid_patterns: list[str] = Field(default_factory=lambda: ["AAAAAAAA", "TTTTTTTT"])
    timeout_seconds: int = 120


class ConstructCfg(_Cfg):
    disclaimer: str
    linker: str = "GPGPG"
    junction_screen_lengths: list[int] = Field(default_factory=lambda: [9, 10])
    junction_ordering: Literal["rank", "greedy"] = "greedy"
    codon: CodonCfg = CodonCfg()
    utr5: str = "hba1"
    utr3: str = "hbb"
    polya_length: int = 100

    @model_validator(mode="after")
    def _disclaimer_present(self) -> ConstructCfg:
        if not self.disclaimer.strip():
            raise ValueError("construct.disclaimer must be non-empty")
        return self


class Settings(_Cfg):
    schema_version: str
    run: RunCfg = RunCfg()
    source: SourceCfg = SourceCfg()
    hla: HlaCfg
    peptides: PeptideCfg = PeptideCfg()
    scoring: ScoringCfg
    selection: SelectionCfg = SelectionCfg()
    mrna: ConstructCfg = Field(alias="construct")


#: Which config subtrees each stage reads. Used to fingerprint a stage so that
#: editing a scoring weight rebuilds ranking onward without redoing prediction.
STAGE_CONFIG_KEYS: dict[str, tuple[str, ...]] = {
    "s1_fetch": ("run", "source"),
    "s2_annotate": ("run", "source"),
    "s3_peptides": ("run", "peptides"),
    "s4_predict": ("run", "hla", "peptides"),
    "s5_rank": ("run", "hla", "scoring", "selection"),
    "s6_construct": ("run", "mrna", "hla"),
}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_settings(paths: list[Path]) -> Settings:
    """Load and validate settings from one or more YAML files, merged in order."""
    merged: dict[str, Any] = {}
    for path in paths:
        if not path.exists():
            raise ConfigError(f"config file not found: {path}")
        with path.open() as fh:
            merged = _deep_merge(merged, yaml.safe_load(fh) or {})
    try:
        return Settings(**merged)
    except Exception as exc:
        raise ConfigError(f"invalid configuration: {exc}") from exc


#: Settings that change how data is fetched, not what is computed. Excluded from
#: stage fingerprints so toggling offline mode does not invalidate cached results.
_TRANSPORT_ONLY: dict[str, set[str]] = {"run": {"offline_mode"}}


def stage_fingerprint(settings: Settings, stage: str) -> str:
    """Hash only the config a given stage reads, ignoring transport-only settings."""
    keys = STAGE_CONFIG_KEYS.get(stage)
    if keys is None:
        raise ConfigError(f"unknown stage {stage!r}")
    dumped = settings.model_dump(mode="json")
    subtree = {}
    for key in keys:
        value = dumped[key]
        ignored = _TRANSPORT_ONLY.get(key)
        if ignored and isinstance(value, dict):
            value = {k: v for k, v in value.items() if k not in ignored}
        subtree[key] = value
    return digest(subtree)
