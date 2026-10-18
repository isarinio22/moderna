"""UniProt sequence client.

UniProt canonical sequences are the reference this pipeline trusts, because they
agree with GRCh37 protein numbering for the genes in question and because they
are stable and citable. Sequences are cached on disk, which is what makes reruns
offline.
"""

from __future__ import annotations

from neoag.io.http import CachedHTTP

BASE_URL = "https://rest.uniprot.org/uniprotkb"
LICENCE = "UniProt data are available under CC BY 4.0."


def parse_fasta(text: str) -> dict[str, str]:
    """Parse FASTA into ``{accession: sequence}``, keyed by bare accession."""
    out: dict[str, str] = {}
    acc: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            if acc:
                out[acc] = "".join(buf)
            parts = line[1:].split("|")
            acc = parts[1] if len(parts) >= 2 else line[1:].split()[0]
            buf = []
        elif acc:
            buf.append(line.strip())
    if acc:
        out[acc] = "".join(buf)
    return out


class UniProtClient:
    def __init__(self, http: CachedHTTP, base_url: str = BASE_URL) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def sequences(self, accessions: list[str], chunk: int = 50) -> dict[str, str]:
        """Fetch canonical sequences, batching where possible.

        Falls back to single-accession requests for anything a batch missed, so
        one bad accession cannot lose a whole chunk.
        """
        wanted = sorted({a for a in accessions if a})
        out: dict[str, str] = {}
        for i in range(0, len(wanted), chunk):
            batch = wanted[i : i + chunk]
            query = " OR ".join(f"accession:{a}" for a in batch)
            try:
                text = self.http.get_text(
                    f"{self.base_url}/stream", params={"query": query, "format": "fasta"}
                )
                out.update(parse_fasta(text))
            except Exception:  # noqa: BLE001 - per-accession retry below
                pass
            for acc in batch:
                if acc in out:
                    continue
                try:
                    out.update(parse_fasta(self.http.get_text(f"{self.base_url}/{acc}.fasta")))
                except Exception:  # noqa: BLE001 - absence is recorded by the caller
                    continue
        return {k: v for k, v in out.items() if v}

    def url_for(self, accession: str) -> str:
        return f"{self.base_url}/{accession}.fasta"
