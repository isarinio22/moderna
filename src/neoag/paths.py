"""Every artifact location in one place.

Nothing elsewhere in the package builds a path by string concatenation, so moving
an output directory is a one-line change here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    """Resolved locations for one run."""

    root: Path = REPO_ROOT

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def cache(self) -> Path:
        return self.data / "cache"

    @property
    def http_cache(self) -> Path:
        return self.cache / "http"

    @property
    def mhcflurry_cache(self) -> Path:
        return self.cache / "mhcflurry"

    @property
    def fixtures(self) -> Path:
        return self.data / "fixtures"

    @property
    def cache_seed(self) -> Path:
        return self.fixtures / "cache_seed"

    @property
    def interim(self) -> Path:
        return self.data / "interim"

    @property
    def processed(self) -> Path:
        return self.data / "processed"

    @property
    def stamps(self) -> Path:
        return self.root / "build" / "stamps"

    @property
    def out(self) -> Path:
        return self.root / "out"

    @property
    def web(self) -> Path:
        return self.out / "web"

    @property
    def figures(self) -> Path:
        return self.root / "figures"

    # Stage artifacts ------------------------------------------------------
    @property
    def mutations(self) -> Path:
        return self.interim / "01_mutations.json"

    @property
    def annotated(self) -> Path:
        return self.interim / "02_annotated.json"

    @property
    def proteome(self) -> Path:
        return self.interim / "02_proteome.json"

    @property
    def peptides(self) -> Path:
        return self.interim / "03_peptides.jsonl"

    @property
    def predictions(self) -> Path:
        return self.interim / "04_predictions.parquet"

    @property
    def ranked(self) -> Path:
        return self.processed / "05_ranked.json"

    @property
    def construct(self) -> Path:
        return self.processed / "06_construct.json"

    @property
    def construct_fasta(self) -> Path:
        return self.processed / "06_construct.fasta"

    def ensure_dirs(self) -> None:
        for path in (
            self.http_cache,
            self.interim,
            self.processed,
            self.stamps,
            self.web,
            self.figures,
        ):
            path.mkdir(parents=True, exist_ok=True)
