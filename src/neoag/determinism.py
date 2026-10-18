"""Determinism controls.

Two runs of this pipeline on the same inputs must produce byte-identical outputs.
The main threats are (a) unseeded RNG, (b) hash-randomised set/dict iteration,
(c) float reduction-order noise from multithreaded tensor maths flipping a rank.

(c) is handled by rounding every score to ``ROUND`` decimals *before* any
comparison or sort, which is cheaper and far less fragile than trying to force
single-threaded deterministic kernels.
"""

from __future__ import annotations

import os
import random

import numpy as np

#: Decimal places every score is rounded to before comparison or sorting.
ROUND = 6


def seed_everything(seed: int) -> None:
    """Seed every RNG this package or its dependencies can reach."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def r(x: float) -> float:
    """Round to the canonical precision used for all comparisons."""
    return round(float(x), ROUND)
