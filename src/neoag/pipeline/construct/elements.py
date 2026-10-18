"""Building blocks of the conceptual construct.

**None of these are real therapeutic sequences.** Working mRNA medicines use
untranslated regions chosen and optimised over many experiments, and those
specific sequences are not reproduced here. The placeholders below are labelled
illustrative blocks: they occupy the right position in the construct and carry a
note explaining what a real one would do, which is the part that teaches
something. Inventing a plausible-looking UTR and presenting it as real would be
the wrong kind of realism.

The elements that *are* genuine are the ones that are standard, published and
short: the Kozak consensus, the stop codons, and the GPGPG spacer widely used in
multi-epitope vaccine design to help the cell cut between epitopes.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Kozak consensus immediately before the start codon; improves translation initiation.
KOZAK = "GCCACC"

#: Two stop codons in a row, a common belt-and-braces choice.
STOP = "TAATAG"

#: Spacer between epitopes. Glycine/proline runs are flexible and discourage the
#: cell's cutting machinery from destroying the epitopes themselves.
DEFAULT_LINKER = "GPGPG"


@dataclass(frozen=True)
class Element:
    """One labelled, non-coding block of the construct."""

    name: str
    sequence: str
    note: str


#: Illustrative untranslated regions. Deliberately generic.
UTR5 = {
    "hba1": Element(
        name="5'UTR (illustrative)",
        sequence="GGGAAATAAGAGAGAAAAGAAGAGTAAGAAGAAATATAAGAGCCACC"[:41],
        note=(
            "Illustrative 5' untranslated region, NOT a real therapeutic sequence. "
            "A real construct uses a UTR optimised for stable, efficient translation; "
            "alpha-globin-derived UTRs are a common starting point in the literature."
        ),
    )
}

UTR3 = {
    "hbb": Element(
        name="3'UTR (illustrative)",
        sequence="GCTCGCTTTCTTGCTGTCCAATTTCTATTAAAGGTTCCTTTGTTCCCTAAGTCCAACTACTAAACTGGGGGATATT"[:76],
        note=(
            "Illustrative 3' untranslated region, NOT a real therapeutic sequence. "
            "A real construct uses a UTR chosen to slow degradation of the mRNA; "
            "beta-globin-derived UTRs are a common starting point in the literature."
        ),
    )
}

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
