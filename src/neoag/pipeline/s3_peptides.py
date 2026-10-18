"""Stage 3 -- turn each validated mutation into candidate peptide pairs.

A cell chops proteins into short fragments and displays them. For a mutation at
protein position *p*, every fragment of length *L* that covers *p* is a possible
display candidate, so all of them are generated and let the predictor decide.

Each mutant peptide is paired with the wild-type peptide from the same window.
That pairing is what makes it possible to ask the question that actually matters:
is the mutant displayed *better than* the normal version? A fragment that is
presented just as well before the mutation teaches the immune system nothing
useful and risks pointing it at healthy tissue.
"""

from __future__ import annotations

import time

from neoag.config import Settings, stage_fingerprint
from neoag.models import AnnotationSet, PeptidePair, ProteomeStore
from neoag.provenance import Provenance
from neoag.util.seq import is_usable_peptide, peptide_at, substitute, windows_spanning

STAGE = "s3_peptides"


def proximal_positions(annotation_set: AnnotationSet) -> dict[str, set[int]]:
    """Mutated positions per protein, used to flag windows carrying two mutations.

    When two somatic mutations fall inside one window, the true peptide depends on
    whether both changes sit on the same copy of the chromosome. Short-read data
    usually cannot say, so these windows are flagged and excluded by default
    rather than guessed at.
    """
    by_protein: dict[str, set[int]] = {}
    for mutation in annotation_set.annotated:
        if mutation.uniprot_acc:
            by_protein.setdefault(mutation.uniprot_acc, set()).add(mutation.protein_position)
    return by_protein


def generate_pairs(
    mutation,
    protein: str,
    lengths: list[int],
    other_positions: set[int],
    exclude_proximal: bool,
) -> list[PeptidePair]:
    """Build every mutant/wild-type peptide pair spanning one mutation."""
    position = mutation.protein_position
    mutant_protein = substitute(protein, position, mutation.aa_alt)
    pairs: list[PeptidePair] = []

    for length in sorted(lengths):
        for start in windows_spanning(len(protein), position, length):
            wt_peptide = peptide_at(protein, start, length)
            mut_peptide = peptide_at(mutant_protein, start, length)
            if not (is_usable_peptide(mut_peptide) and is_usable_peptide(wt_peptide)):
                continue

            window = set(range(start, start + length))
            others = (window & other_positions) - {position}
            flags: list[str] = []
            if others:
                flags.append("proximal_mutation")
                if exclude_proximal:
                    continue
            if start == 1:
                flags.append("at_protein_start")
            if start + length - 1 == len(protein):
                flags.append("at_protein_end")

            pairs.append(
                PeptidePair(
                    peptide_pair_id=f"{mutation.mutation_id}|{start}|{length}",
                    mutation_id=mutation.mutation_id,
                    gene=mutation.raw.hugo_symbol,
                    uniprot_acc=mutation.uniprot_acc or "",
                    length=length,
                    peptide_start=start,
                    mut_offset=position - start + 1,
                    mut_peptide=mut_peptide,
                    wt_peptide=wt_peptide,
                    protein_position=position,
                    expression_rsem=mutation.expression_rsem,
                    flags=flags,
                )
            )
    return pairs


def dedupe(pairs: list[PeptidePair]) -> list[PeptidePair]:
    """Collapse pairs with identical sequences, keeping a deterministic survivor.

    Two different windows -- or two nearby mutations -- can yield the same
    mutant/wild-type sequence pair. Predicting it twice wastes time and would
    double-count it during ranking.
    """
    best: dict[tuple[str, str], PeptidePair] = {}
    for pair in sorted(pairs, key=lambda p: p.peptide_pair_id):
        best.setdefault((pair.mut_peptide, pair.wt_peptide), pair)
    return sorted(best.values(), key=lambda p: p.peptide_pair_id)


def run(
    settings: Settings, annotation_set: AnnotationSet, proteome: ProteomeStore
) -> list[PeptidePair]:
    """Execute stage 3."""
    started = time.monotonic()
    positions = proximal_positions(annotation_set)
    pairs: list[PeptidePair] = []

    for mutation in annotation_set.annotated:
        protein = proteome.sequences.get(mutation.uniprot_acc or "")
        if not protein:
            continue
        pairs.extend(
            generate_pairs(
                mutation,
                protein,
                settings.peptides.lengths,
                positions.get(mutation.uniprot_acc or "", set()),
                settings.peptides.exclude_proximal_mutations,
            )
        )

    deduped = dedupe(pairs)
    run.last_provenance = Provenance(  # type: ignore[attr-defined]
        stage=STAGE,
        origin=annotation_set.provenance.origin,
        created_utc=Provenance.now_utc(),
        config_fingerprint=stage_fingerprint(settings, STAGE),
        wall_seconds=round(time.monotonic() - started, 3),
        counts={
            "mutations": len(annotation_set.annotated),
            "pairs_generated": len(pairs),
            "pairs_after_dedupe": len(deduped),
        },
    )
    return deduped
