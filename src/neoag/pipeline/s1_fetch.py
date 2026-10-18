"""Stage 1 -- fetch somatic variants and expression for one tumour sample.

Reads a de-identified, open-access TCGA melanoma sample through the cBioPortal
public API, or a committed synthetic sample for offline and CI runs.

Every variant that does not make it through is recorded in ``dropped`` with a
reason. Nothing is discarded silently.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from neoag.config import Settings, stage_fingerprint
from neoag.io.cbioportal import CBioPortalClient
from neoag.models import DropRecord, ExpressionValue, MutationSet, RawMutation
from neoag.paths import Paths
from neoag.provenance import Provenance

STAGE = "s1_fetch"

#: The twenty standard amino acids. Excludes X (unknown), U (selenocysteine) and
#: * (stop), none of which can anchor a usable peptide.
STANDARD_AA = "ACDEFGHIKLMNPQRSTVWY"

#: Protein change as cBioPortal reports it: no ``p.`` prefix, e.g. ``V600E``.
_PROTEIN_CHANGE = re.compile(rf"^(?:p\.)?([{STANDARD_AA}])(\d+)([{STANDARD_AA}])$")


def parse_protein_change(value: str) -> tuple[str, int, str] | None:
    """Parse a simple substitution into (reference aa, 1-based position, alternate aa).

    Returns ``None`` for anything that is not a single-residue substitution --
    frameshifts, in-frame indels, splice variants and nonsense changes all land
    here and are dropped with a reason.
    """
    match = _PROTEIN_CHANGE.match((value or "").strip())
    if not match:
        return None
    ref, pos, alt = match.group(1), int(match.group(2)), match.group(3)
    return (ref, pos, alt) if pos >= 1 and ref != alt else None


def parse_mutation(record: dict[str, Any], sample_id: str) -> RawMutation | DropRecord:
    """Convert one cBioPortal record into a validated model."""
    gene = (record.get("gene") or {}).get("hugoGeneSymbol") or record.get("hugoGeneSymbol")
    identifier = f"{gene}:{record.get('startPosition')}"
    if not gene:
        return DropRecord(identifier=identifier, stage=STAGE, reason="no_gene_symbol")
    try:
        return RawMutation(
            sample_id=record.get("sampleId", sample_id),
            hugo_symbol=gene,
            entrez_gene_id=int(record["entrezGeneId"]),
            chromosome=str(record["chr"]).replace("chr", ""),
            start_position=int(record["startPosition"]),
            end_position=int(record["endPosition"]),
            reference_allele=record["referenceAllele"],
            variant_allele=record["variantAllele"],
            protein_change=record.get("proteinChange") or "",
            mutation_type=record.get("mutationType") or "",
            variant_type=record.get("variantType") or "",
            refseq_mrna_id=record.get("refseqMrnaId"),
            protein_pos_start=record.get("proteinPosStart"),
            protein_pos_end=record.get("proteinPosEnd"),
            ncbi_build=record.get("ncbiBuild") or "GRCh37",
        )
    except (KeyError, TypeError, ValueError) as exc:
        return DropRecord(
            identifier=identifier, stage=STAGE, reason="unparseable_record", detail=str(exc)
        )


def filter_mutations(
    mutations: list[RawMutation], settings: Settings, expression: dict[int, float | None]
) -> tuple[list[RawMutation], list[DropRecord]]:
    """Keep simple missense substitutions, capped at a deterministic maximum."""
    kept: list[RawMutation] = []
    dropped: list[DropRecord] = []
    allowed_mut = set(settings.source.mutation_types)
    allowed_var = set(settings.source.variant_types)

    for mutation in mutations:
        if mutation.mutation_type not in allowed_mut:
            dropped.append(
                DropRecord(
                    identifier=mutation.mutation_id,
                    stage=STAGE,
                    reason="mutation_type_excluded",
                    detail=mutation.mutation_type,
                )
            )
            continue
        if mutation.variant_type not in allowed_var:
            dropped.append(
                DropRecord(
                    identifier=mutation.mutation_id,
                    stage=STAGE,
                    reason="variant_type_excluded",
                    detail=mutation.variant_type,
                )
            )
            continue
        if parse_protein_change(mutation.protein_change) is None:
            dropped.append(
                DropRecord(
                    identifier=mutation.mutation_id,
                    stage=STAGE,
                    reason="not_a_simple_substitution",
                    detail=mutation.protein_change,
                )
            )
            continue
        kept.append(mutation)

    # Deduplicate identical calls before capping.
    seen: set[str] = set()
    unique: list[RawMutation] = []
    for mutation in kept:
        if mutation.mutation_id in seen:
            dropped.append(
                DropRecord(identifier=mutation.mutation_id, stage=STAGE, reason="duplicate_call")
            )
            continue
        seen.add(mutation.mutation_id)
        unique.append(mutation)

    cap = settings.source.max_mutations
    if len(unique) > cap:
        # Prefer expressed genes, then a stable key, so the cap is deterministic
        # rather than dependent on API ordering.
        ordered = sorted(
            unique,
            key=lambda m: (-(expression.get(m.entrez_gene_id) or 0.0), m.mutation_id),
        )
        for mutation in ordered[cap:]:
            dropped.append(
                DropRecord(
                    identifier=mutation.mutation_id,
                    stage=STAGE,
                    reason="over_max_mutations",
                    detail=f"cap={cap}",
                )
            )
        unique = sorted(ordered[:cap], key=lambda m: m.mutation_id)
    else:
        unique = sorted(unique, key=lambda m: m.mutation_id)

    return unique, dropped


def load_synthetic(path: Path, settings: Settings) -> MutationSet:
    """Load the committed synthetic sample.

    Clearly labelled as synthetic in its provenance, which propagates all the way
    to the website so it can never be mistaken for measured tumour data.
    """
    payload = json.loads(path.read_text())
    mutations = [RawMutation.model_validate(m) for m in payload["mutations"]]
    expression = [ExpressionValue.model_validate(e) for e in payload.get("expression", [])]
    return MutationSet(
        study_id=payload.get("study_id", "synthetic"),
        sample_id=payload.get("sample_id", settings.source.sample_id),
        genome_build=payload.get("genome_build", "GRCh37"),
        mutations=sorted(mutations, key=lambda m: m.mutation_id),
        expression=expression,
        provenance=Provenance(
            stage=STAGE,
            origin="synthetic",
            created_utc=Provenance.now_utc(),
            config_fingerprint=stage_fingerprint(settings, STAGE),
            counts={"mutations": len(mutations)},
            notes=[
                "SYNTHETIC SAMPLE. Invented variants in real genes, for offline and CI runs. "
                "Does not correspond to any real tumour or person."
            ],
        ),
    )


def run(settings: Settings, paths: Paths, client: CBioPortalClient | None = None) -> MutationSet:
    """Execute stage 1."""
    started = time.monotonic()
    if settings.source.use_synthetic:
        return load_synthetic(paths.fixtures / "synthetic_sample.json", settings)

    if client is None:
        raise ValueError("a CBioPortalClient is required unless source.use_synthetic is set")

    study_id = settings.source.study_id
    sample_id = settings.source.sample_id
    raw = client.mutations(study_id, [sample_id])

    parsed = [parse_mutation(r, sample_id) for r in raw]
    mutations = [m for m in parsed if isinstance(m, RawMutation)]
    dropped = [d for d in parsed if isinstance(d, DropRecord)]

    gene_ids = sorted({m.entrez_gene_id for m in mutations})
    expression_records = client.expression(study_id, [sample_id], gene_ids)
    by_gene: dict[int, float | None] = {
        int(r["entrezGeneId"]): (float(r["value"]) if r.get("value") is not None else None)
        for r in expression_records
        if r.get("entrezGeneId") is not None
    }

    kept, more_dropped = filter_mutations(mutations, settings, by_gene)
    dropped.extend(more_dropped)

    symbols = {m.entrez_gene_id: m.hugo_symbol for m in kept}
    expression = [
        ExpressionValue(entrez_gene_id=gid, hugo_symbol=symbols[gid], rsem=by_gene.get(gid))
        for gid in sorted(symbols)
    ]

    return MutationSet(
        study_id=study_id,
        sample_id=sample_id,
        genome_build=settings.source.genome_build,
        mutations=kept,
        expression=expression,
        dropped=dropped,
        provenance=Provenance(
            stage=STAGE,
            origin="cbioportal",
            created_utc=Provenance.now_utc(),
            config_fingerprint=stage_fingerprint(settings, STAGE),
            wall_seconds=round(time.monotonic() - started, 3),
            counts={
                "records_returned": len(raw),
                "mutations_kept": len(kept),
                "dropped": len(dropped),
                "genes_with_expression": sum(1 for v in by_gene.values() if v is not None),
            },
        ),
    )
