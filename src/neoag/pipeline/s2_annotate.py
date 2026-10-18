"""Stage 2 -- resolve each variant to a protein position, and check it.

This is the stage that decides whether everything downstream is correct.

A variant call says "valine 600 became glutamate". To build peptides we need the
protein sequence around position 600 -- and if the sequence we fetch uses
different numbering, position 600 is a different residue, every peptide spanning
it is wrong, and **nothing raises an error**. The output looks entirely normal.

So the reference amino acid is verified against the sequence before any peptide
is generated. A disagreement is a rejection, never a warning. If disagreements
exceed a configured share of the sample, the run aborts: that pattern means the
genome builds do not match, and no amount of per-variant handling can rescue it.
"""

from __future__ import annotations

import time

from neoag.config import Settings, stage_fingerprint
from neoag.errors import ReferenceMismatchError
from neoag.io.ensembl_grch37 import Ensembl37Client
from neoag.io.genome_nexus import GenomeNexusClient, TranscriptPick
from neoag.io.uniprot import UniProtClient
from neoag.models import (
    AnnotatedMutation,
    AnnotationSet,
    DropRecord,
    MutationSet,
    ProteomeStore,
    RefAAValidation,
    SequenceMeta,
)
from neoag.paths import Paths
from neoag.pipeline.s1_fetch import parse_protein_change
from neoag.provenance import Provenance
from neoag.util.hashing import digest_text

STAGE = "s2_annotate"


def validate_reference(
    sequence: str | None,
    position: int,
    expected_aa: str,
    source: str | None = None,
) -> RefAAValidation:
    """Check that ``sequence`` really has ``expected_aa`` at 1-based ``position``.

    The only gate between a genome-build mismatch and a plausible wrong answer.
    """
    src = source  # type: ignore[assignment]
    if not sequence:
        return RefAAValidation(
            status="no_sequence", expected_aa=expected_aa, message="no protein sequence available"
        )
    if position < 1 or position > len(sequence):
        return RefAAValidation(
            status="position_out_of_range",
            expected_aa=expected_aa,
            sequence_source=src,
            message=f"position {position} outside protein of length {len(sequence)}",
        )
    observed = sequence[position - 1]
    if observed != expected_aa:
        return RefAAValidation(
            status="mismatch",
            expected_aa=expected_aa,
            observed_aa=observed,
            sequence_source=src,
            message=(
                f"sequence has {observed} at position {position}, variant call expects "
                f"{expected_aa}. Usually a genome-build or isoform mismatch."
            ),
        )
    return RefAAValidation(
        status="ok", expected_aa=expected_aa, observed_aa=observed, sequence_source=src
    )


def run(
    settings: Settings,
    paths: Paths,
    mutation_set: MutationSet,
    genome_nexus: GenomeNexusClient | None = None,
    uniprot: UniProtClient | None = None,
    ensembl: Ensembl37Client | None = None,
    fixture_proteome: dict[str, str] | None = None,
) -> tuple[AnnotationSet, ProteomeStore]:
    """Execute stage 2."""
    started = time.monotonic()
    expression = {e.entrez_gene_id: e.rsem for e in mutation_set.expression}
    dropped: list[DropRecord] = []

    # 1. Parse the protein change. Anything unparseable never reached here from
    #    stage 1, but a synthetic fixture could carry one.
    parsed: dict[str, tuple[str, int, str]] = {}
    for mutation in mutation_set.mutations:
        change = parse_protein_change(mutation.protein_change)
        if change is None:
            dropped.append(
                DropRecord(
                    identifier=mutation.mutation_id,
                    stage=STAGE,
                    reason="not_a_simple_substitution",
                    detail=mutation.protein_change,
                )
            )
            continue
        parsed[mutation.mutation_id] = change

    # 2. Resolve transcript and UniProt accession.
    picks: dict[str, TranscriptPick] = {}
    if genome_nexus is not None:
        wanted = [m.hgvs_g for m in mutation_set.mutations if m.mutation_id in parsed]
        annotations = genome_nexus.annotate(wanted)
        for mutation in mutation_set.mutations:
            if mutation.mutation_id not in parsed:
                continue
            record = annotations.get(mutation.hgvs_g)
            if record:
                ref_aa, pos, _ = parsed[mutation.mutation_id]
                picks[mutation.mutation_id] = _pick(record, ref_aa, pos)

    # Some sources carry the accession inline; use it when annotation did not
    # resolve one (this is how the offline synthetic fixture works).
    for mutation in mutation_set.mutations:
        if mutation.mutation_id not in parsed:
            continue
        existing = picks.get(mutation.mutation_id)
        if mutation.uniprot_acc and not (existing and existing.uniprot_acc):
            ref_aa, pos, alt = parsed[mutation.mutation_id]
            picks[mutation.mutation_id] = TranscriptPick(
                None, mutation.uniprot_acc, None, ref_aa, alt, pos
            )

    # 3. Fetch protein sequences.
    accessions = sorted({p.uniprot_acc for p in picks.values() if p.uniprot_acc})
    sequences: dict[str, str] = {}
    meta: dict[str, SequenceMeta] = {}
    if fixture_proteome is not None:
        for acc in accessions:
            seq = fixture_proteome.get(acc)
            if not seq:
                continue
            sequences[acc] = seq
            meta[acc] = SequenceMeta(
                accession=acc,
                source="synthetic_fixture",
                url="committed fixture: data/fixtures/synthetic_proteome.fasta",
                length=len(seq),
                sha=digest_text(seq),
            )
    elif accessions and uniprot is not None:
        for acc, seq in uniprot.sequences(accessions).items():
            sequences[acc] = seq
            meta[acc] = SequenceMeta(
                accession=acc,
                source="uniprot",
                url=uniprot.url_for(acc),
                length=len(seq),
                sha=digest_text(seq),
            )

    # 4. Validate, with a GRCh37 Ensembl fallback for anything UniProt could not settle.
    annotated: list[AnnotatedMutation] = []
    rejected: list[AnnotatedMutation] = []

    for mutation in mutation_set.mutations:
        if mutation.mutation_id not in parsed:
            continue
        ref_aa, position, alt_aa = parsed[mutation.mutation_id]
        pick = picks.get(mutation.mutation_id)

        if pick is None or not pick.uniprot_acc:
            rejected.append(
                _build(mutation, pick, ref_aa, alt_aa, position, expression, None,
                       RefAAValidation(status="no_accession", expected_aa=ref_aa,
                                       message="no UniProt accession resolved"))
            )
            continue

        acc = pick.uniprot_acc
        sequence = sequences.get(acc)
        source = meta[acc].source if acc in meta else None
        validation = validate_reference(sequence, position, ref_aa, source)

        if validation.status != "ok" and ensembl is not None and pick.transcript_id:
            fallback_seq = ensembl.protein_sequence(pick.transcript_id)
            fallback = validate_reference(fallback_seq, position, ref_aa, "ensembl_grch37")
            if fallback.status == "ok" and fallback_seq:
                key = pick.transcript_id
                sequences[key] = fallback_seq
                meta[key] = SequenceMeta(
                    accession=key,
                    source="ensembl_grch37",
                    url=ensembl.url_for(key),
                    length=len(fallback_seq),
                    sha=digest_text(fallback_seq),
                )
                acc, validation = key, fallback

        record = _build(
            mutation, pick, ref_aa, alt_aa, position, expression,
            len(sequences[acc]) if acc in sequences else None, validation, acc,
        )
        (annotated if validation.ok else rejected).append(record)

    result = AnnotationSet(
        sample_id=mutation_set.sample_id,
        annotated=sorted(annotated, key=lambda m: m.mutation_id),
        rejected=sorted(rejected, key=lambda m: m.mutation_id),
        dropped=dropped,
        provenance=Provenance(
            stage=STAGE,
            origin=mutation_set.provenance.origin,
            created_utc=Provenance.now_utc(),
            config_fingerprint=stage_fingerprint(settings, STAGE),
            wall_seconds=round(time.monotonic() - started, 3),
            counts={
                "input": len(mutation_set.mutations),
                "annotated": len(annotated),
                "rejected": len(rejected),
                "proteins": len(sequences),
            },
        ),
    )

    # 5. A high mismatch rate is a systematic problem, not a run of bad luck.
    fraction = result.mismatch_fraction
    limit = settings.run.max_mismatch_fraction
    if fraction > limit:
        raise ReferenceMismatchError(
            f"{fraction:.1%} of resolved variants disagree with their protein sequence "
            f"(limit {limit:.0%}). This is the signature of a genome-build mismatch: "
            f"TCGA positions are GRCh37. Every peptide built from these would be wrong."
        )

    store = ProteomeStore(
        sequences=dict(sorted(sequences.items())),
        meta=dict(sorted(meta.items())),
        provenance=Provenance(
            stage=STAGE, origin=mutation_set.provenance.origin, created_utc=Provenance.now_utc()
        ),
    )
    return result, store


def _pick(record: dict, ref_aa: str, position: int) -> TranscriptPick:
    from neoag.io.genome_nexus import pick_transcript

    return pick_transcript(record, ref_aa, position)


def _build(
    mutation,
    pick: TranscriptPick | None,
    ref_aa: str,
    alt_aa: str,
    position: int,
    expression: dict[int, float | None],
    protein_length: int | None,
    validation: RefAAValidation,
    accession: str | None = None,
) -> AnnotatedMutation:
    return AnnotatedMutation(
        mutation_id=mutation.mutation_id,
        raw=mutation,
        transcript_id=pick.transcript_id if pick else None,
        uniprot_acc=accession or (pick.uniprot_acc if pick else None),
        hgvsp_short=(pick.hgvsp_short if pick else None) or f"p.{ref_aa}{position}{alt_aa}",
        aa_ref=ref_aa,
        aa_alt=alt_aa,
        protein_position=position,
        protein_length=protein_length,
        expression_rsem=expression.get(mutation.entrez_gene_id),
        validation=validation,
    )
