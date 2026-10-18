"""Assemble the labelled, conceptual mRNA construct."""

from __future__ import annotations

from neoag.config import ConstructCfg
from neoag.models import ConstructBlock, JunctionReport, ScoredEpitope
from neoag.pipeline.construct.codon import optimize_cds
from neoag.pipeline.construct.elements import CAP_NOTE, KOZAK, MODIFIED_BASE_NOTE, STOP, UTR3, UTR5
from neoag.util.seq import gc_content


def build_protein(order: list[str], epitopes: dict[str, ScoredEpitope], linker: str) -> str:
    """Join the selected epitopes with linkers into one protein sequence."""
    return linker.join(epitopes[eid].mut_peptide for eid in order)


def assemble(
    order: list[str],
    epitopes: dict[str, ScoredEpitope],
    cfg: ConstructCfg,
    seed: int,
    junctions: list[JunctionReport],
) -> tuple[str, list[ConstructBlock], str, str, dict[str, bool]]:
    """Build the full sequence and its block map.

    Returns ``(full_sequence, blocks, cds_aa, optimizer, constraints)``.
    """
    linker = cfg.linker
    cds_aa = build_protein(order, epitopes, linker)
    codon = optimize_cds(cds_aa, cfg.codon, seed)
    cds = codon.cds

    utr5 = UTR5[cfg.utr5]
    utr3 = UTR3[cfg.utr3]
    polya = "A" * cfg.polya_length

    blocks: list[ConstructBlock] = []
    cursor = 0

    def add(name: str, kind: str, sequence: str, note: str = "", aa: str | None = None,
            epitope_id: str | None = None) -> None:
        nonlocal cursor
        blocks.append(
            ConstructBlock(
                name=name, kind=kind, start=cursor, end=cursor + len(sequence),
                sequence=sequence, aa_sequence=aa, note=note, source_epitope_id=epitope_id,
            )
        )
        cursor += len(sequence)

    # The cap is a chemical modification, so it is a zero-length labelled block.
    add("5' cap", "cap", "", CAP_NOTE)
    add(utr5.name, "utr", utr5.sequence, utr5.note)
    add("Kozak", "kozak", KOZAK, "Consensus sequence that helps the ribosome start in the right place.")

    # Walk the coding sequence, labelling each epitope and linker in nucleotides.
    offset = 0
    for index, epitope_id in enumerate(order):
        peptide = epitopes[epitope_id].mut_peptide
        nt = len(peptide) * 3
        add(
            f"epitope_{index + 1:02d}",
            "epitope",
            cds[offset : offset + nt],
            f"{epitopes[epitope_id].gene} {epitopes[epitope_id].mut_peptide} "
            f"(best allele {epitopes[epitope_id].best_allele})",
            aa=peptide,
            epitope_id=epitope_id,
        )
        offset += nt
        if index < len(order) - 1:
            lnt = len(linker) * 3
            add(
                f"linker_{index + 1:02d}", "linker", cds[offset : offset + lnt],
                "Flexible spacer so the cell's machinery cuts between epitopes, not through them.",
                aa=linker,
            )
            offset += lnt

    add("stop", "stop", STOP, "Two stop codons in a row.")
    add(utr3.name, "utr", utr3.sequence, utr3.note)
    add("poly-A tail", "polya", polya,
        f"{cfg.polya_length} adenines. Protects the message from being chewed up too quickly.")

    full = "".join(b.sequence for b in blocks)
    constraints = dict(codon.constraints_satisfied)
    constraints["blocks_tile_sequence"] = _blocks_tile(blocks, full)
    return full, blocks, cds_aa, codon.optimizer, constraints


def _blocks_tile(blocks: list[ConstructBlock], full: str) -> bool:
    """Every block must sit end to end with no gaps or overlaps."""
    cursor = 0
    for block in blocks:
        if block.start != cursor:
            return False
        cursor = block.end
    return cursor == len(full)


def to_fasta(sample_id: str, sequence: str, disclaimer: str) -> str:
    """FASTA with the disclaimer in the header, so it travels with the sequence."""
    header = f">{sample_id}_conceptual_construct | {' '.join(disclaimer.split())}"
    body = "\n".join(sequence[i : i + 60] for i in range(0, len(sequence), 60))
    return f"{header}\n{body}\n"


def summarize(full: str, cds_aa: str) -> dict[str, float | int]:
    return {
        "gc_content": round(gc_content(full), 4),
        "cds_length_nt": len(cds_aa) * 3,
        "total_length_nt": len(full),
    }


__all__ = ["assemble", "build_protein", "summarize", "to_fasta", "MODIFIED_BASE_NOTE"]
