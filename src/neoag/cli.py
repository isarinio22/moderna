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
from neoag.models import AnnotationSet, MRNAConstruct, MutationSet, PeptidePair, ProteomeStore, RankingResult
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
        f"stage 2: {len(annotation_set.annotated)} validated, {len(annotation_set.rejected)} rejected "
        f"({mismatches} reference-amino-acid mismatches) -> {paths.annotated.relative_to(paths.root)}"
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
        f"(panel {args.panel or settings.hla.primary_panel}) -> {paths.ranked.relative_to(paths.root)}"
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


def cmd_config_stamp(args: argparse.Namespace) -> int:
    settings = _settings(args)
    stamp = {"stage": args.stage, "fingerprint": stage_fingerprint(settings, args.stage)}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
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
    print(f"validated muts  {len(annotation_set.annotated)} ({len(annotation_set.rejected)} rejected)")
    print(f"candidates      {len(ranking.epitopes)}")
    print(f"selected        {len(selected)}")
    print(f"construct       {construct.total_length_nt} nt, GC {construct.gc_content:.1%}")
    print()
    print(f"{'rank':>4}  {'gene':<10} {'peptide':<12} {'allele':<13} {'nM':>9}  {'score':>6}")
    for epitope in selected[:10]:
        print(
            f"{epitope.rank:>4}  {epitope.gene:<10} {epitope.mut_peptide:<12} "
            f"{epitope.best_allele:<13} {epitope.mut_affinity_nm:>9.1f}  {epitope.components.total:>6.3f}"
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
    ]:
        p = sub.add_parser(name, help=helptext)
        p.set_defaults(func=func)

    p_rank = sub.add_parser("rank", help="stage 5: score, rank and select")
    p_rank.add_argument("--panel", default=None, help="HLA panel name (default: primary)")
    p_rank.set_defaults(func=cmd_rank)

    p_stamp = sub.add_parser("config-stamp", help="write a per-stage config fingerprint")
    p_stamp.add_argument("--stage", required=True)
    p_stamp.add_argument("--out", required=True)
    p_stamp.set_defaults(func=cmd_config_stamp)

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
