"""Build the committed synthetic sample used for offline and CI runs.

Writes ``data/fixtures/synthetic_sample.json`` and ``synthetic_proteome.fasta``.

The sample is **invented**, but it is invented carefully:

* The genes are real genes recurrently mutated in melanoma, with their real
  UniProt accessions and real protein sequences.
* Each mutation's reference amino acid is read from the real sequence, so the
  fixture is internally consistent and exercises the reference check honestly
  rather than bypassing it.
* Genomic coordinates are deliberately fake (chromosome ``SYN``) so nothing here
  can be mistaken for a real variant call.
* Everything is seeded, so re-running this script reproduces the file byte for
  byte.

No real patient's data is used. Run with::

    .venv/bin/python scripts/build_fixtures.py
"""

from __future__ import annotations

import json
import random
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
SEED = 20261018

# Real genes recurrently altered in cutaneous melanoma, with UniProt accessions.
# Very large proteins (TTN, MUC16) are excluded to keep the fixture small.
GENES: list[tuple[str, str]] = [
    ("BRAF", "P15056"), ("NRAS", "P01111"), ("TP53", "P04637"), ("CDKN2A", "P42771"),
    ("PTEN", "P60484"), ("NF1", "P21359"), ("KIT", "P10721"), ("RAC1", "P63000"),
    ("PPP6C", "O00743"), ("ARID2", "Q68CP9"), ("IDH1", "O75874"), ("MAP2K1", "Q02750"),
    ("KRAS", "P01116"), ("EGFR", "P00533"), ("CTNNB1", "P35222"), ("RB1", "P06400"),
    ("PIK3CA", "P42336"), ("SMAD4", "Q13485"), ("FBXW7", "Q969H0"), ("DDX3X", "O00571"),
    ("RASA2", "Q15283"), ("GRIN2A", "Q12879"), ("ERBB4", "Q15303"), ("MITF", "O75030"),
    ("SF3B1", "O75533"), ("GNAQ", "P50148"), ("GNA11", "Q9Y4J8"), ("CDK4", "P11802"),
    ("MDM2", "Q00987"), ("AKT1", "P31749"), ("STK19", "P49842"), ("TERT", "O14746"),
    ("ROS1", "P08922"), ("MAP3K1", "Q13233"), ("PPP1R3A", "Q16821"), ("TACC1", "O75410"),
    ("ADAMTS18", "Q8TE60"), ("DCC", "P43146"), ("ATM", "Q13315"), ("SMARCA4", "P51532"),
]

STANDARD_AA = "ACDEFGHIKLMNPQRSTVWY"
UA = {"User-Agent": "neoag-fixture-builder/0.1 (educational)"}


def fetch(url: str, retries: int = 4) -> str:
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=45
            ).read().decode()
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} after {exc}", file=sys.stderr)
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def fetch_entry(accession: str) -> tuple[str, int | None]:
    """Return (sequence, NCBI gene id) for one accession."""
    url = (
        f"https://rest.uniprot.org/uniprotkb/{accession}"
        "?format=json&fields=sequence,xref_geneid"
    )
    data = json.loads(fetch(url))
    sequence = data["sequence"]["value"]
    gene_id = next(
        (int(x["id"]) for x in data.get("uniProtKBCrossReferences", []) if x["database"] == "GeneID"),
        None,
    )
    return sequence, gene_id


def main() -> int:
    rng = random.Random(SEED)
    FIXTURES.mkdir(parents=True, exist_ok=True)

    proteome: dict[str, str] = {}
    mutations: list[dict] = []
    expression: list[dict] = []

    for index, (symbol, accession) in enumerate(GENES):
        print(f"[{index + 1:2d}/{len(GENES)}] {symbol} ({accession})", file=sys.stderr)
        sequence, gene_id = fetch_entry(accession)
        if gene_id is None:
            print(f"  no GeneID for {accession}; skipping", file=sys.stderr)
            continue
        proteome[accession] = sequence

        # One or two mutations per gene, at positions well inside the protein so
        # both terminal and interior window behaviour gets exercised.
        for k in range(1 + (1 if rng.random() < 0.15 else 0)):
            for _ in range(40):
                position = rng.randint(2, max(2, len(sequence) - 1))
                ref = sequence[position - 1]
                if ref in STANDARD_AA:
                    break
            else:
                continue
            alt = rng.choice([a for a in STANDARD_AA if a != ref])
            mutations.append(
                {
                    "sample_id": "SYNTHETIC-MEL-001",
                    "hugo_symbol": symbol,
                    "entrez_gene_id": gene_id,
                    "chromosome": "SYN",
                    "start_position": (index + 1) * 1000 + k,
                    "end_position": (index + 1) * 1000 + k,
                    "reference_allele": "A",
                    "variant_allele": "T",
                    "protein_change": f"{ref}{position}{alt}",
                    "mutation_type": "Missense_Mutation",
                    "variant_type": "SNP",
                    "uniprot_acc": accession,
                    "protein_pos_start": position,
                    "protein_pos_end": position,
                    "ncbi_build": "GRCh37",
                }
            )

        expression.append(
            {
                "entrez_gene_id": gene_id,
                "hugo_symbol": symbol,
                # Log-normal, roughly the shape of real RSEM values.
                "rsem": round(float(rng.lognormvariate(4.0, 1.6)), 4),
            }
        )

    mutations.sort(key=lambda m: (m["hugo_symbol"], m["start_position"]))
    payload = {
        "_warning": (
            "SYNTHETIC SAMPLE. Invented mutations in real genes with real protein "
            "sequences. Genomic coordinates are deliberately fake (chromosome 'SYN'). "
            "This does not correspond to any real tumour or person, and must not be "
            "interpreted as data. Regenerate with scripts/build_fixtures.py."
        ),
        "study_id": "synthetic",
        "sample_id": "SYNTHETIC-MEL-001",
        "genome_build": "GRCh37",
        "seed": SEED,
        "mutations": mutations,
        "expression": sorted(expression, key=lambda e: e["hugo_symbol"]),
    }

    (FIXTURES / "synthetic_sample.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = ["# Real UniProt canonical sequences for the synthetic fixture's genes.",
             "# Sequences are real; the mutations in synthetic_sample.json are invented."]
    for acc in sorted(proteome):
        seq = proteome[acc]
        lines.append(f">{acc}")
        lines.extend(seq[i : i + 60] for i in range(0, len(seq), 60))
    (FIXTURES / "synthetic_proteome.fasta").write_text("\n".join(lines) + "\n")

    print(
        f"\nwrote {len(mutations)} mutations across {len(proteome)} proteins "
        f"({sum(len(s) for s in proteome.values()):,} aa)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
