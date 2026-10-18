"""Provenance records.

Every artifact this pipeline writes carries one of these in a sidecar file, so
"is this output reproducible?" is answered by diffing two JSON files rather than
by trusting a memory of how it was produced.
"""

from __future__ import annotations

import datetime as _dt
import platform
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from neoag import SCHEMA_VERSION, __version__

#: Where a dataset came from. This is load-bearing: it is what stops simulated or
#: synthetic data being presented as though it were measured.
DataOrigin = Literal["cbioportal", "synthetic", "reconstructed", "illustrative_simulation"]


def _tool_versions() -> dict[str, str]:
    versions = {"python": sys.version.split()[0], "platform": platform.machine()}
    for name in ("pydantic", "pandas", "numpy", "mhcflurry", "torch", "dnachisel", "lifelines"):
        try:
            mod = __import__(name)
        except ImportError:
            continue
        versions[name] = str(getattr(mod, "__version__", getattr(mod, "VERSION", "unknown")))
    return versions


class Provenance(BaseModel):
    """How one artifact was produced."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: str
    origin: DataOrigin
    neoag_version: str = __version__
    schema_version: str = SCHEMA_VERSION
    config_fingerprint: str = ""
    input_fingerprints: dict[str, str] = Field(default_factory=dict)
    tool_versions: dict[str, str] = Field(default_factory=_tool_versions)
    created_utc: str = ""
    wall_seconds: float = 0.0
    counts: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    @staticmethod
    def now_utc() -> str:
        return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat()

    @property
    def is_real_measurement(self) -> bool:
        """False for anything invented: synthetic samples and simulated trial data."""
        return self.origin in ("cbioportal", "reconstructed")
