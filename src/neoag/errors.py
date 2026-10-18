"""Exception hierarchy.

Every failure mode that can produce a *wrong answer* rather than a crash gets its
own exception type, so it can never be caught by a broad ``except Exception`` and
quietly downgraded to a warning.
"""

from __future__ import annotations


class NeoagError(Exception):
    """Base class for every error this package raises."""


class ConfigError(NeoagError):
    """Configuration failed validation."""


class CacheMissError(NeoagError):
    """Offline mode was requested and the response was not in the cache."""


class ApiClientError(NeoagError):
    """A public API returned a non-retryable error."""


class ForbiddenHostError(NeoagError):
    """A request was aimed at a host this package refuses to use.

    Raised for GRCh38 Ensembl endpoints. Mixing genome builds silently produces
    wrong protein positions, so the wrong host is blocked rather than discouraged.
    """


class ReferenceMismatchError(NeoagError):
    """The reference amino acid in a protein sequence disagrees with the variant call.

    Raised only when the *rate* of mismatches exceeds the configured threshold,
    which indicates a systematic genome-build problem rather than a handful of
    stale annotations.
    """


class StaleArtifactError(NeoagError):
    """An input artifact changed since the downstream artifact was built."""


class PredictorUnavailableError(NeoagError):
    """The requested presentation predictor could not be loaded."""
