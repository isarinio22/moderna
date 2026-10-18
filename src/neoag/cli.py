"""Command line interface.

Each stage is a subcommand reading and writing explicit files, so stages can be
run, inspected and re-run independently. ``run-all`` chains them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from neoag import __version__
from neoag.artifacts import read_json, read_jsonl, write_json, write_jsonl
from neoag.config import Settings, load_settings, stage_fingerprint
from neoag.determinism import seed_everything
from neoag.io.cache import HttpCache
from neoag.io.cbioportal import CBioPortalClient
from neoag.io.ensembl_grch37 import Ensembl37Client
from neoag.io.genome_nexus import GenomeNexusClient
from neoag.io.http import CachedHTTP
from neoag.io.uniprot import UniProtClient, parse_fasta
from neoag.models import (
    AnnotationSet,
    MRNAConstruct,
    MutationSet,
    PeptidePair,
    ProteomeStore,
    RankingResult,
)
from neoag.paths import Paths
from neoag.pipeline import s1_fetch, s2_annotate, s3_peptides, s4_predict, s5_rank, s6_construct
from neoag.pipeline.construct.assemble import to_fasta
from neoag.pipeline.predictors.base import load_predictor


def _settings(args: argparse.Namespace) -> Settings:
    configs = [Path(c) for c in args.config]
    settings = load_settings(configs)
    seed_everything(settings.run.seed)
    return settings


def _http(settings: Settings, paths: Paths) -> CachedHTTP:
    cache = HttpCache(paths.http_cache)
    seeded = cache.seed_from(paths.cache_seed)
    if seeded:
        print(f"seeded {seeded} cached responses from the repository", file=sys.stderr)
    return CachedHTTP(cache, settings.run.offline_mode, seed=settings.run.seed)


def _fixture_proteome(paths: Paths) -> dict[str, str]:
    return parse_fasta((paths.fixtures / "synthetic_proteome.fasta").read_text())


# -- stages ----------------------------------------------------------------- #

def cmd_fetch(args: argparse.Namespace) -> int:
    settings, paths = _settings(args), Paths()
    paths.ensure_dirs()
    client = None if settings.source.use_synthetic else CBioPortalClient(_http(settings, paths))
    result = s1_fetch.run(settings, paths, client)
    write_json(paths.mutations, result, result.provenance)
    print(
        f"stage 1: {len(result.mutations)} mutations kept, {len(result.dropped)} dropped "
        f"-> {paths.mutations.relative_to(paths.root)}"
    )
    return 0


def cmd_annotate(args: argparse.Namespace) -> int:
    settings, paths = _settings(args), Paths()
    mutation_set = read_json(paths.mutations, MutationSet)
    if settings.source.use_synthetic:
        annotation_set, proteome = s2_annotate.run(
            settings, paths, mutation_set, fixture_proteome=_fixture_proteome(paths)
        )
    else:
        http = _http(settings, paths)
        annotation_set, proteome = s2_annotate.run(
            settings, paths, mutation_set,
            GenomeNexusClient(http), UniProtClient(http), Ensembl37Client(http),
        )
    write_json(paths.annotated, annotation_set, annotation_set.provenance)
    write_json(paths.proteome, proteome)
    mismatches = sum(1 for m in annotation_set.rejected if m.validation.status == "mismatch")
    print(
        f"stage 2: {len(annotation_set.annotated)} validated, "
        f"{len(annotation_set.rejected)} rejected ({mismatches} reference-amino-acid "
        f"mismatches) -> {paths.annotated.relative_to(paths.root)}"
    )
    return 0


def cmd_peptides(args: argparse.Namespace) -> int:
    settings, paths = _settings(args), Paths()
    annotation_set = read_json(paths.annotated, AnnotationSet)
    proteome = read_json(paths.proteome, ProteomeStore)
    pairs = s3_peptides.run(settings, annotation_set, proteome)
    write_jsonl(paths.peptides, pairs, getattr(s3_peptides.run, "last_provenance", None))
    print(f"stage 3: {len(pairs)} peptide pairs -> {paths.peptides.relative_to(paths.root)}")
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    settings, paths = _settings(args), Paths()
    pairs = read_jsonl(paths.peptides, PeptidePair)
    predictor = load_predictor(settings.run.predictor, paths.mhcflurry_cache)
    frame, provenance = s4_predict.run(settings, pairs, predictor)
    paths.predictions.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(paths.predictions, index=False)
    Path(str(paths.predictions) + ".meta.json").write_text(
        json.dumps(provenance.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    )
    print(
        f"stage 4: {len(frame)} predictions over {frame['allele'].nunique()} alleles "
        f"using {getattr(predictor, 'name', '?')} -> {paths.predictions.relative_to(paths.root)}"
    )
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    settings, paths = _settings(args), Paths()
    pairs = read_jsonl(paths.peptides, PeptidePair)
    predictions = pd.read_parquet(paths.predictions)
    annotation_set = read_json(paths.annotated, AnnotationSet)
    result = s5_rank.run(settings, pairs, predictions, annotation_set, args.panel)
    write_json(paths.ranked, result, result.provenance)
    print(
        f"stage 5: {len(result.selected_ids)} selected from {len(result.epitopes)} candidates "
        f"(panel {args.panel or settings.hla.primary_panel}) "
        f"-> {paths.ranked.relative_to(paths.root)}"
    )
    return 0


def cmd_construct(args: argparse.Namespace) -> int:
    settings, paths = _settings(args), Paths()
    ranking = read_json(paths.ranked, RankingResult)
    predictor = load_predictor(settings.run.predictor, paths.mhcflurry_cache)
    construct = s6_construct.run(settings, ranking, predictor)
    write_json(paths.construct, construct, construct.provenance)
    paths.construct_fasta.write_text(
        to_fasta(construct.sample_id, construct.full_sequence, construct.disclaimer)
    )
    print(
        f"stage 6: {len(construct.epitope_order)} epitopes, {construct.total_length_nt} nt, "
        f"GC {construct.gc_content:.1%}, optimizer {construct.codon_optimizer} "
        f"-> {paths.construct.relative_to(paths.root)}"
    )
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    for step in (cmd_fetch, cmd_annotate, cmd_peptides, cmd_predict, cmd_rank, cmd_construct):
        code = step(args)
        if code != 0:
            return code
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Write every JSON payload the website reads."""
    from neoag.export import export_all

    settings, paths = _settings(args), Paths()
    outdir = Path(args.outdir) if args.outdir else paths.root / "site" / "data"

    mutations = read_json(paths.mutations, MutationSet)
    annotations = read_json(paths.annotated, AnnotationSet)
    pairs = read_jsonl(paths.peptides, PeptidePair)
    predictions = pd.read_parquet(paths.predictions)
    construct = read_json(paths.construct, MRNAConstruct)

    # Rank once per HLA panel. Predictions already cover every allele, so this is
    # cheap, and it is what lets the site show how the chosen set depends on who
    # the patient is.
    rankings = {
        name: s5_rank.run(settings, pairs, predictions, annotations, name)
        for name in settings.hla.panels
    }

    predictor_name = "unknown"
    meta = Path(str(paths.predictions) + ".meta.json")
    if meta.exists():
        for note in json.loads(meta.read_text()).get("notes", []):
            if note.startswith("predictor="):
                predictor_name = note.split("=", 1)[1]

    sizes = export_all(
        outdir, settings, mutations, annotations, rankings, construct,
        predictions, predictor_name,
    )
    total = sum(sizes.values())
    for name, size in sorted(sizes.items()):
        print(f"  {name:<18} {size / 1024:>8.1f} KB")
    print(f"  {'total':<18} {total / 1024:>8.1f} KB -> {outdir.relative_to(paths.root)}")
    return 0


def cmd_figures(args: argparse.Namespace) -> int:
    """Render the static PNG version of every interactive figure."""
    from neoag.figures.build import build_all

    paths = Paths()
    data_dir = Path(args.data) if args.data else paths.root / "site" / "data"
    outdir = Path(args.outdir) if args.outdir else paths.figures
    written = build_all(data_dir, outdir, args.only)
    for name, path in sorted(written.items()):
        print(f"  {name:<22} {path.stat().st_size / 1024:>7.1f} KB  {path.name}")
    print(f"  {len(written)} figures -> {outdir.relative_to(paths.root)}")
    return 0


def cmd_carousel(args: argparse.Namespace) -> int:
    """Build the LinkedIn carousel PDF and its slide PNGs."""
    from neoag.figures.carousel import build, build_pngs

    paths = Paths()
    data_dir = Path(args.data) if args.data else paths.root / "site" / "data"
    outdir = paths.root / "linkedin"
    pdf = build(data_dir, outdir / "carousel.pdf")
    pngs = build_pngs(data_dir, outdir / "slides")
    print(f"  carousel.pdf   {pdf.stat().st_size / 1024:>7.1f} KB  {len(pngs)} slides")
    print(f"  slides/        {len(pngs)} PNGs at 1080x1350")
    return 0


def cmd_animation(args: argparse.Namespace) -> int:
    """Render the pipeline animation to MP4."""
    from neoag.figures.animation import build

    paths = Paths()
    data_dir = Path(args.data) if args.data else paths.root / "site" / "data"
    out = build(data_dir, paths.root / "linkedin" / "pipeline.mp4")
    print(f"  pipeline.mp4   {out.stat().st_size / 1024 / 1024:>7.1f} MB")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """Reconstruct the trial data, refit it, and report the discrepancies."""
    from neoag.evidence.derived import (
        absolute_risk_difference,
        number_needed_to_treat,
        restricted_mean_difference,
    )
    from neoag.evidence.honesty import verdict
    from neoag.evidence.published import AT_RISK_RFS_5YR, RFS_5YEAR
    from neoag.evidence.reconstruct import placement_sensitivity, reconstruct
    from neoag.evidence.refit import refit
    from neoag.evidence.validate import validate

    paths = Paths()
    paths.ensure_dirs()
    data = reconstruct(AT_RISK_RFS_5YR, RFS_5YEAR.events)
    result = refit(data)
    report = validate(result, RFS_5YEAR)

    print(f"KEYNOTE-942 recurrence-free survival, data cutoff {RFS_5YEAR.cutoff}")
    print(f"reconstructed {len(data)} patient records "
          f"({int(data.event.sum())} recurrences) from the published at-risk table\n")
    print(report.to_markdown())
    print()

    sensitivity = placement_sensitivity(AT_RISK_RFS_5YR, RFS_5YEAR.events)
    print(f"event-placement sensitivity: hazard ratio varies by "
          f"{sensitivity.spread:.4f} across all placement rules\n")

    combo, control = result.fitter("combo"), result.fitter("control")
    print(f"{'timepoint':>12}  {'extra event-free per 100':>26}  number needed to treat")
    for t in (18.0, 24.0, 36.0, 48.0, 60.0):
        rd = absolute_risk_difference(combo, control, t)
        nnt = number_needed_to_treat(rd)
        interval = f"[{rd.ci_low * 100:+.1f}, {rd.ci_high * 100:+.1f}]"
        print(f"{t:>9.0f} mo  {rd.per_100:>8.1f} {interval:>17}  {nnt.display}")

    rmst = restricted_mean_difference(combo, control, 60.0)
    print(f"\nrestricted mean event-free time to 5 years: "
          f"{rmst.treated_months:.1f} vs {rmst.control_months:.1f} months "
          f"({rmst.difference_months:+.1f})")

    out = paths.web / "evidence.md"
    out.write_text(
        f"# Reconstruction of KEYNOTE-942 recurrence-free survival\n\n"
        f"Data cutoff {RFS_5YEAR.cutoff}. Source: {RFS_5YEAR.source}\n\n"
        f"{report.to_markdown()}\n\n"
        f"## Sensitivity to the one assumption\n\n{sensitivity.format_table()}\n\n"
        f"## Bottom line\n\n{verdict()}\n"
    )
    print(f"\nwrote {out.relative_to(paths.root)}")
    return 0 if report.passed else 1


def cmd_config_stamp(args: argparse.Namespace) -> int:
    settings = _settings(args)
    stamp = {"stage": args.stage, "fingerprint": stage_fingerprint(settings, args.stage)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_config_stamps(args: argparse.Namespace) -> int:
    """Write a fingerprint file per stage, touching only those that changed.

    Make decides what to rebuild from file timestamps, so a stamp must be
    rewritten when and only when its stage's configuration actually changed.
    Writing unconditionally would rebuild everything on every invocation;
    relying on the config file's own timestamp is worse, because restoring a
    file from backup or checking out an older revision moves its timestamp
    *backwards* and make then skips a rebuild that is genuinely needed.
    """
    from neoag.config import STAGE_CONFIG_KEYS

    settings = _settings(args)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    changed = []
    for stage in STAGE_CONFIG_KEYS:
        target = outdir / f"{stage}.json"
        content = json.dumps(
            {"stage": stage, "fingerprint": stage_fingerprint(settings, stage)},
            indent=2, sort_keys=True,
        ) + "\n"
        if not target.exists() or target.read_text() != content:
            target.write_text(content)
            changed.append(stage)
    if changed and not args.quiet:
        print(f"config changed for: {', '.join(changed)}", file=sys.stderr)
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Print a human-readable summary of the most recent run."""
    paths = Paths()
    annotation_set = read_json(paths.annotated, AnnotationSet)
    ranking = read_json(paths.ranked, RankingResult)
    construct = read_json(paths.construct, MRNAConstruct)
    selected = [e for e in ranking.epitopes if e.selected]
    print(f"sample          {ranking.sample_id}")
    print(f"origin          {ranking.provenance.origin}")
    print(f"HLA alleles     {', '.join(ranking.hla_alleles)}")
    rejected = len(annotation_set.rejected)
    print(f"validated muts  {len(annotation_set.annotated)} ({rejected} rejected)")
    print(f"candidates      {len(ranking.epitopes)}")
    print(f"selected        {len(selected)}")
    print(f"construct       {construct.total_length_nt} nt, GC {construct.gc_content:.1%}")
    print()
    print(f"{'rank':>4}  {'gene':<10} {'peptide':<12} {'allele':<13} {'nM':>9}  {'score':>6}")
    for epitope in selected[:10]:
        print(
            f"{epitope.rank:>4}  {epitope.gene:<10} {epitope.mut_peptide:<12} "
            f"{epitope.best_allele:<13} {epitope.mut_affinity_nm:>9.1f}  "
            f"{epitope.components.total:>6.3f}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neoag", description=__doc__)
    parser.add_argument("--version", action="version", version=f"neoag {__version__}")
    parser.add_argument(
        "-c", "--config", action="append", default=None,
        help="config YAML; repeat to overlay (later files win)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, helptext in [
        ("fetch", cmd_fetch, "stage 1: fetch mutations and expression"),
        ("annotate", cmd_annotate, "stage 2: resolve proteins and validate reference residues"),
        ("peptides", cmd_peptides, "stage 3: generate mutant/wild-type peptide pairs"),
        ("predict", cmd_predict, "stage 4: predict MHC-I presentation"),
        ("construct", cmd_construct, "stage 6: assemble the conceptual mRNA"),
        ("run-all", cmd_run_all, "run every stage in order"),
        ("summary", cmd_summary, "print a summary of the last run"),
        ("evidence", cmd_evidence, "reconstruct and validate the trial statistics"),
    ]:
        p = sub.add_parser(name, help=helptext)
        p.set_defaults(func=func)

    p_rank = sub.add_parser("rank", help="stage 5: score, rank and select")
    p_rank.add_argument("--panel", default=None, help="HLA panel name (default: primary)")
    p_rank.set_defaults(func=cmd_rank)

    p_car = sub.add_parser("carousel", help="build the LinkedIn carousel")
    p_car.add_argument("--data", default=None)
    p_car.set_defaults(func=cmd_carousel)

    p_anim = sub.add_parser("animation", help="render the pipeline animation to MP4")
    p_anim.add_argument("--data", default=None)
    p_anim.set_defaults(func=cmd_animation)

    p_figs = sub.add_parser("figures", help="render static PNG figures")
    p_figs.add_argument("--data", default=None)
    p_figs.add_argument("--outdir", default=None)
    p_figs.add_argument("--only", default=None)
    p_figs.set_defaults(func=cmd_figures)

    p_export = sub.add_parser("export", help="write the website's JSON payloads")
    p_export.add_argument("--outdir", default=None)
    p_export.set_defaults(func=cmd_export)

    p_stamp = sub.add_parser("config-stamp", help="write one stage's config fingerprint")
    p_stamp.add_argument("--stage", required=True)
    p_stamp.add_argument("--out", required=True)
    p_stamp.set_defaults(func=cmd_config_stamp)

    p_stamps = sub.add_parser("config-stamps", help="write all stage fingerprints")
    p_stamps.add_argument("--outdir", required=True)
    p_stamps.add_argument("--quiet", action="store_true")
    p_stamps.set_defaults(func=cmd_config_stamps)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.config:
        args.config = ["config/default.yaml"]
    if not hasattr(args, "panel"):
        args.panel = None
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
