"""Export everything the website needs as plain JSON.

The site is static: no build step, no framework, no server. It reads these files
directly, which means the numbers on the page are the numbers the pipeline
produced, and anyone can download them and check.

Two things are carried deliberately into every payload:

* **Provenance.** Each file records whether it came from real tumour data or a
  synthetic fixture, and whether predictions came from a real model or the stub.
  The page renders that, so a demo run can never be mistaken for a result.
* **The discards.** Candidates that were rejected, and why, ship alongside the
  ones that were chosen. The funnel is the most honest part of the story.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from neoag import SCHEMA_VERSION, __version__
from neoag.config import Settings
from neoag.models import AnnotationSet, MRNAConstruct, MutationSet, RankingResult
from neoag.provenance import Provenance

#: Candidates shipped to the browser. Enough for the ranking view to be
#: explorable without making the page heavy on a phone.
MAX_EPITOPES_EXPORTED = 600


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(float(value), digits)


def write(path: Path, payload: Any) -> int:
    """Write canonical JSON and return the byte size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def manifest(
    settings: Settings,
    mutations: MutationSet,
    annotations: AnnotationSet,
    ranking: RankingResult,
    construct: MRNAConstruct,
    predictor_name: str,
) -> dict[str, Any]:
    """Run metadata, assumptions and limitations, rendered at the top of the page."""
    is_real = mutations.provenance.origin == "cbioportal"
    return {
        "schema_version": SCHEMA_VERSION,
        "neoag_version": __version__,
        "generated_utc": Provenance.now_utc(),
        "sample": {
            "id": mutations.sample_id,
            "study": mutations.study_id,
            "genome_build": mutations.genome_build,
            "origin": mutations.provenance.origin,
            "is_real_tumour_data": is_real,
        },
        "predictor": {
            "name": predictor_name,
            "is_real_prediction": not predictor_name.startswith("stub"),
        },
        "hla": {
            "primary_panel": settings.hla.primary_panel,
            "panels": settings.hla.panels,
            "assumption": " ".join(settings.hla.assumption_note.split()),
        },
        "counts": {
            "mutations_returned": mutations.provenance.counts.get("records_returned", 0),
            "mutations_kept": len(mutations.mutations),
            "mutations_validated": len(annotations.annotated),
            "mutations_rejected": len(annotations.rejected),
            "candidates": len(ranking.epitopes),
            "selected": len(ranking.selected_ids),
            "construct_nt": construct.total_length_nt,
        },
        "disclaimers": [
            "Educational project. Not medical advice.",
            "Not affiliated with, endorsed by, or reviewed by Moderna or Merck.",
            "mRNA-4157 / V940 (intismeran autogene) is investigational and is not "
            "approved by any regulator anywhere.",
            "The design pipeline is a simplified teaching simulation, not the real "
            "manufacturing process.",
        ],
        "limitations": [
            "HLA type is assumed, not measured. The public tumour data carries none, "
            "and a different HLA type would select different peptides from the "
            "identical tumour.",
            "No matched normal sample, so some variants here may be inherited rather "
            "than acquired by the tumour.",
            "No variant phasing or clonality: mutations present in only part of the "
            "tumour are treated the same as those in every cell.",
            "No immunogenicity model. Being presented is not the same as provoking a "
            "useful T-cell response.",
            "No self-proteome subtraction, and no manufacturing constraints.",
        ],
    }


def funnel(
    mutations: MutationSet, annotations: AnnotationSet, ranking: RankingResult
) -> list[dict[str, Any]]:
    """The narrowing from raw mutations to the final set, with reasons at each step."""
    from collections import Counter

    dropped_s1 = Counter(d.reason for d in mutations.dropped)
    rejected_s2 = Counter(m.validation.status for m in annotations.rejected)
    excluded = Counter(
        e.exclusion_reason for e in ranking.epitopes if e.exclusion_reason is not None
    )
    returned = mutations.provenance.counts.get("records_returned", len(mutations.mutations))

    return [
        {
            "step": "mutations found",
            "label": "Every change the tumour made to a protein",
            "n_in": returned,
            "n_out": len(mutations.mutations),
            "reasons": dict(dropped_s1),
        },
        {
            "step": "protein verified",
            "label": "Mutations we could place on a real, checked protein sequence",
            "n_in": len(mutations.mutations),
            "n_out": len(annotations.annotated),
            "reasons": dict(rejected_s2),
        },
        {
            "step": "fragments generated",
            "label": "Short pieces spanning each mutation, with their normal twins",
            "n_in": len(annotations.annotated),
            "n_out": len(ranking.epitopes),
            "reasons": {},
        },
        {
            "step": "displayed and ranked",
            "label": "Fragments the immune system could actually see, scored",
            "n_in": len(ranking.epitopes),
            "n_out": len(ranking.selected_ids),
            "reasons": dict(excluded),
        },
    ]


def epitopes(ranking: RankingResult, limit: int = MAX_EPITOPES_EXPORTED) -> dict[str, Any]:
    """Scored candidates, compact enough for a phone.

    Every selected epitope is included regardless of the limit; the rest are the
    highest scoring, which is what the ranking view shows.
    """
    ordered = sorted(ranking.epitopes, key=lambda e: e.rank)
    selected = [e for e in ordered if e.selected]
    others = [e for e in ordered if not e.selected][: max(0, limit - len(selected))]
    shown = sorted(selected + others, key=lambda e: e.rank)

    return {
        "panel": ranking.hla_alleles,
        "weights": ranking.weights,
        "total_candidates": len(ranking.epitopes),
        "exported": len(shown),
        "epitopes": [
            {
                "id": e.peptide_pair_id,
                "rank": e.rank,
                "gene": e.gene,
                "mut": e.mut_peptide,
                "wt": e.wt_peptide,
                "pos": e.protein_position,
                "offset": e.mut_offset,
                "allele": e.best_allele,
                "nm": _round(e.mut_affinity_nm, 1),
                "wt_nm": _round(e.wt_affinity_nm, 1),
                "pres": _round(e.mut_presentation_score),
                "pct": _round(e.mut_presentation_percentile, 3),
                "agreto": _round(e.agretopicity_ratio, 3),
                "expr": _round(e.expression_percentile, 3),
                "c": {
                    "presentation": _round(e.components.presentation),
                    "agretopicity": _round(e.components.agretopicity),
                    "expression": _round(e.components.expression),
                    "quality": _round(e.components.quality),
                },
                "score": _round(e.components.total),
                "sel": e.selected,
                "why_not": e.exclusion_reason,
            }
            for e in shown
        ],
    }


def panels(rankings: dict[str, RankingResult]) -> dict[str, Any]:
    """How the chosen set changes with HLA type.

    This is the clearest demonstration of why the therapy is individualised: the
    identical tumour yields a different set of targets for a different person.
    """
    out: dict[str, Any] = {"panels": {}}
    selected_by_panel = {}
    for name, ranking in rankings.items():
        chosen = [e for e in ranking.epitopes if e.selected]
        selected_by_panel[name] = {e.peptide_pair_id for e in chosen}
        out["panels"][name] = {
            "alleles": ranking.hla_alleles,
            "selected": [
                {
                    "id": e.peptide_pair_id, "gene": e.gene, "mut": e.mut_peptide,
                    "allele": e.best_allele, "score": _round(e.components.total),
                }
                for e in sorted(chosen, key=lambda e: e.rank)
            ],
        }

    names = sorted(selected_by_panel)
    shared = set.intersection(*selected_by_panel.values()) if selected_by_panel else set()
    out["overlap"] = {
        "shared_by_all": len(shared),
        "pairwise": {
            f"{a}|{b}": len(selected_by_panel[a] & selected_by_panel[b])
            for i, a in enumerate(names)
            for b in names[i + 1 :]
        },
    }
    return out


def construct_payload(construct: MRNAConstruct) -> dict[str, Any]:
    """The conceptual construct as a block map the page can draw."""
    return {
        "disclaimer": construct.disclaimer,
        "is_conceptual": True,
        "total_nt": construct.total_length_nt,
        "cds_nt": construct.cds_length_nt,
        "gc": _round(construct.gc_content, 4),
        "optimizer": construct.codon_optimizer,
        "constraints": construct.constraints_satisfied,
        "blocks": [
            {
                "name": b.name, "kind": b.kind, "start": b.start, "end": b.end,
                "nt": b.end - b.start, "aa": b.aa_sequence, "note": b.note,
                "epitope": b.source_epitope_id,
            }
            for b in construct.blocks
        ],
        "junctions": [
            {
                "i": j.junction_index,
                "worst_percentile": _round(j.worst_percentile, 3),
                "strong_binders": j.n_strong_binders,
            }
            for j in construct.junction_report
        ],
        "notes": construct.provenance.notes,
    }


def evidence_payload() -> dict[str, Any]:
    """Everything from Part 2: curves, landmarks, derived quantities, caveats."""
    from neoag.evidence.derived import (
        absolute_risk_difference,
        number_needed_to_treat,
        restricted_mean_difference,
    )
    from neoag.evidence.honesty import EXPLAINERS, verdict
    from neoag.evidence.published import AT_RISK_RFS_5YR, RFS_5YEAR, RFS_CUTS, TRIAL
    from neoag.evidence.reconstruct import placement_sensitivity, reconstruct
    from neoag.evidence.refit import refit
    from neoag.evidence.validate import validate

    data = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
    result = refit(data)
    report = validate(result, RFS_5YEAR)
    sensitivity = placement_sensitivity(AT_RISK_RFS_5YR, RFS_5YEAR.events)

    curves: dict[str, Any] = {}
    for arm in ("combo", "control"):
        fitter = result.fitter(arm)
        frame = fitter.survival_function_
        curves[arm] = {
            "t": [round(float(t), 3) for t in frame.index],
            "s": [round(float(v), 5) for v in frame.iloc[:, 0]],
            "n_risk": [
                {"t": t, "n": n}
                for t, n in zip(
                    AT_RISK_RFS_5YR[arm].times_months, AT_RISK_RFS_5YR[arm].n_risk, strict=True
                )
            ],
        }

    landmarks = []
    for t in (18.0, 24.0, 36.0, 48.0, 60.0):
        rd = absolute_risk_difference(result.fitter("combo"), result.fitter("control"), t)
        nnt = number_needed_to_treat(rd)
        landmarks.append(
            {
                "months": t,
                "combo": _round(rd.treated_survival),
                "control": _round(rd.control_survival),
                "per_100": round(rd.per_100, 1),
                "ci_low_per_100": round(rd.ci_low * 100, 1),
                "ci_high_per_100": round(rd.ci_high * 100, 1),
                "crosses_zero": rd.crosses_zero,
                "nnt": nnt.display,
                "published_combo": RFS_5YEAR.landmarks["combo"].get(t),
                "published_control": RFS_5YEAR.landmarks["control"].get(t),
            }
        )

    rmst = restricted_mean_difference(result.fitter("combo"), result.fitter("control"), 60.0)

    return {
        "trial": TRIAL,
        "cuts": [
            {
                "name": name,
                "cutoff": cut.cutoff,
                "median_followup_months": cut.median_followup_months,
                "hr": cut.hazard_ratio,
                "ci": [cut.ci_low, cut.ci_high],
                "p": cut.p_value,
                "p_sided": cut.p_value_sided,
                "p_is_nominal": cut.p_value_is_nominal,
                "events": cut.events,
                "note": " ".join(cut.note.split()),
                "source": cut.source,
            }
            for name, cut in RFS_CUTS.items()
        ],
        "reconstruction": {
            "hr": _round(result.hazard_ratio, 4),
            "ci": [_round(result.ci_low, 4), _round(result.ci_high, 4)],
            "p_one_sided": _round(result.p_value_one_sided, 5),
            "events": result.events,
            "n": result.n,
            "median_months": {
                k: _round(v, 2) for k, v in result.median_survival.items()
            },
            "placement_sensitivity": {
                "hr_by_placement": {k: round(v, 4) for k, v in sensitivity.results.items()},
                "spread": round(sensitivity.spread, 4),
            },
            "proportional_hazards": {
                "p": _round(result.proportional_hazards.p_value, 4),
                "violated": result.proportional_hazards.violated,
                "caveat": result.proportional_hazards.caveat,
            },
        },
        "curves": curves,
        "landmarks": landmarks,
        "rmst": {
            "horizon_months": rmst.horizon_months,
            "combo": round(rmst.treated_months, 2),
            "control": round(rmst.control_months, 2),
            "difference": round(rmst.difference_months, 2),
        },
        "validation": {
            "passed": report.passed,
            "markdown": report.to_markdown(),
            "checks": [
                {
                    "name": c.name,
                    "reconstructed": _round(c.reconstructed, 5),
                    "published": _round(c.published, 5),
                    "difference": _round(c.difference, 5),
                    "status": c.status,
                    "note": c.note,
                }
                for c in report.checks
            ],
        },
        "explainers": {
            key: {
                "title": e.title,
                "plain": " ".join(e.plain.split()),
                "technical": " ".join(e.technical.split()),
                "caveats": [" ".join(c.split()) for c in e.caveats],
                "sources": list(e.sources),
            }
            for key, e in EXPLAINERS.items()
        },
        "verdict": verdict(),
    }


def export_all(
    outdir: Path,
    settings: Settings,
    mutations: MutationSet,
    annotations: AnnotationSet,
    rankings: dict[str, RankingResult],
    construct: MRNAConstruct,
    predictions: pd.DataFrame,
    predictor_name: str,
) -> dict[str, int]:
    """Write every payload and return the size of each in bytes."""
    primary = rankings[settings.hla.primary_panel]
    sizes = {
        "manifest.json": write(
            outdir / "manifest.json",
            manifest(settings, mutations, annotations, primary, construct, predictor_name),
        ),
        "funnel.json": write(outdir / "funnel.json", funnel(mutations, annotations, primary)),
        "epitopes.json": write(outdir / "epitopes.json", epitopes(primary)),
        "panels.json": write(outdir / "panels.json", panels(rankings)),
        "construct.json": write(outdir / "construct.json", construct_payload(construct)),
        "evidence.json": write(outdir / "evidence.json", evidence_payload()),
    }
    return sizes
