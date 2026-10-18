"""Building blocks of the conceptual construct.

The untranslated regions here are **real human sequences**, fetched from Ensembl
and committed with their provenance in ``data/fixtures/utr_elements.json``
(regenerate with ``scripts/fetch_utrs.py``).

They come from the globin genes, which are the standard worked example in the
mRNA therapeutics literature: globin messages are unusually long-lived, which is
how a red blood cell precursor keeps producing haemoglobin after discarding its
nucleus. That stability is a property of the untranslated regions, and it is why
globin UTRs are a common starting point when designing a therapeutic message.

What is *not* claimed: these are not the untranslated regions used in any
particular product. Real constructs use regions refined over many experiments,
and those specific sequences are not public. These are the published,
citable example -- a real thing that demonstrates the real principle.

The remaining elements are standard and short: the Kozak consensus, stop codons,
and the GPGPG spacer widely used in multi-epitope vaccine design.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

#: Kozak consensus immediately before the start codon; improves translation initiation.
KOZAK = "GCCACC"

#: Two stop codons in a row, a common belt-and-braces choice.
STOP = "TAATAG"

#: Spacer between epitopes. Glycine/proline runs are flexible and discourage the
#: cell's cutting machinery from destroying the epitopes themselves.
DEFAULT_LINKER = "GPGPG"

#: The signal that tells the cell where to attach the poly-A tail. Present in the
#: real beta-globin 3' UTR, which is worth pointing out: the tail is not simply
#: appended, it is placed.
POLYA_SIGNAL = "AATAAA"

_FIXTURE = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "utr_elements.json"


@dataclass(frozen=True)
class Element:
    """One labelled, non-coding block of the construct."""

    name: str
    sequence: str
    note: str
    source: str = ""
    transcript_id: str = ""


@lru_cache(maxsize=1)
def _load() -> dict[str, dict]:
    return json.loads(_FIXTURE.read_text())["elements"]


def _element(key: str, name: str, extra: str) -> Element:
    record = _load()[key]
    note = (
        f"{record['description']} Real sequence, {record['length']} nt, from "
        f"{record['transcript_id']} ({record['assembly']}). {extra}"
    )
    return Element(
        name=name,
        sequence=record["sequence"],
        note=note.strip(),
        source=record["source"],
        transcript_id=record["transcript_id"],
    )


def utr5(key: str) -> Element:
    """The 5' untranslated region: everything the ribosome reads before the protein starts."""
    return _element(
        f"{key}_utr5",
        "5' UTR (human alpha-globin)",
        "Sits between the cap and the start codon, and strongly affects how efficiently "
        "the message is translated.",
    )


def utr3(key: str) -> Element:
    """The 3' untranslated region: what follows the stop codon."""
    element = _element(
        f"{key}_utr3",
        "3' UTR (human beta-globin)",
        "Follows the stop codon and governs how long the message survives before being "
        "broken down.",
    )
    if POLYA_SIGNAL in element.sequence:
        offset = element.sequence.index(POLYA_SIGNAL)
        return Element(
            name=element.name,
            sequence=element.sequence,
            note=(
                f"{element.note} Contains the {POLYA_SIGNAL} polyadenylation signal at "
                f"position {offset + 1}, which marks where the poly-A tail is added."
            ),
            source=element.source,
            transcript_id=element.transcript_id,
        )
    return element


#: The 5' cap is a chemical modification, not a nucleotide, so it is represented
#: as a zero-length labelled block rather than invented letters.
CAP_NOTE = (
    "m7G(5')ppp(5')N cap. A chemical modification at the 5' end, not a base, so it "
    "has no letters in the sequence. The cap is what tells the cell this is a real "
    "message worth translating rather than debris worth destroying."
)

#: Modified bases are likewise a chemistry choice, not a sequence choice.
MODIFIED_BASE_NOTE = (
    "Therapeutic mRNA typically replaces uridine with a modified base such as "
    "N1-methylpseudouridine, which greatly reduces the innate immune response to the "
    "RNA itself. That is a chemistry choice invisible in the letters below."
)
