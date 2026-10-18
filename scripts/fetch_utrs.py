"""Fetch the real untranslated regions used by the conceptual construct.

Writes ``data/fixtures/utr_elements.json`` with the sequences and full
provenance: transcript, source URL, length and checksum.

The 5' and 3' UTRs of the human globin genes are the standard worked example in
the mRNA therapeutics literature -- they are unusually stable messages, which is
why red blood cell precursors can keep translating them after losing their
nucleus. Fetching them rather than hard-coding them means the sequence in this
repository is checkable against its source.

UTR boundaries are derived by locating the coding sequence inside the full
cDNA, which avoids any genomic coordinate or strand arithmetic. The script
asserts the coding sequence appears exactly once before trusting the split.

Run with::

    .venv/bin/python scripts/fetch_utrs.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fixtures" / "utr_elements.json"

# GRCh37 deliberately: the rest of this project pins that assembly, and
# neoag.io.http blocks the GRCh38 host outright.
BASE = "https://grch37.rest.ensembl.org"

WANTED = [
    ("HBA1", "utr5", "Human alpha-globin 5' untranslated region."),
    ("HBB", "utr3", "Human beta-globin 3' untranslated region."),
]


def get(path: str, **params: object) -> dict:
    query = ";".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE}{path}" + (f"?{query}" if query else "")
    request = urllib.request.Request(
        url, headers={"User-Agent": "neoag-educational/0.1", "Accept": "application/json"}
    )
    for attempt in range(4):
        try:
            return json.loads(urllib.request.urlopen(request, timeout=45).read().decode())
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f"  retry after {exc}", file=sys.stderr)
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def split_utrs(transcript_id: str) -> tuple[str, str]:
    """Return (5' UTR, 3' UTR) by locating the CDS within the cDNA."""
    cdna = get(f"/sequence/id/{transcript_id}", type="cdna")["seq"]
    cds = get(f"/sequence/id/{transcript_id}", type="cds")["seq"]
    if cdna.count(cds) != 1:
        raise RuntimeError(
            f"{transcript_id}: coding sequence appears {cdna.count(cds)} times in the cDNA; "
            "refusing to guess the UTR boundaries"
        )
    start = cdna.index(cds)
    return cdna[:start], cdna[start + len(cds) :]


def main() -> int:
    elements: dict[str, dict] = {}
    for symbol, kind, description in WANTED:
        print(f"fetching {symbol} {kind}", file=sys.stderr)
        gene = get(f"/lookup/symbol/homo_sapiens/{symbol}", expand=1)
        canonical = [t for t in gene["Transcript"] if t.get("is_canonical")] or gene["Transcript"]
        transcript = canonical[0]
        utr5, utr3 = split_utrs(transcript["id"])
        sequence = utr5 if kind == "utr5" else utr3
        if not sequence:
            raise RuntimeError(f"{symbol}: empty {kind}")

        elements[f"{symbol.lower()}_{kind}"] = {
            "gene_symbol": symbol,
            "kind": kind,
            "sequence": sequence,
            "length": len(sequence),
            "sha256": hashlib.sha256(sequence.encode()).hexdigest(),
            "transcript_id": transcript["id"],
            "assembly": "GRCh37",
            "source": f"{BASE}/sequence/id/{transcript['id']}?type=cdna",
            "fetched_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
            "description": description,
        }
        print(f"  {transcript['id']}  {len(sequence)} nt", file=sys.stderr)

    payload = {
        "_note": (
            "Real human untranslated regions from Ensembl GRCh37, used as labelled "
            "blocks in the conceptual construct. Regenerate with scripts/fetch_utrs.py. "
            "Ensembl data are available under the Apache 2.0 licence; the underlying "
            "genome sequence is public domain."
        ),
        "elements": dict(sorted(elements.items())),
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
