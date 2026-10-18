"""The JSON payloads the website reads."""

from __future__ import annotations

import json

import pytest

from neoag.export import MAX_EPITOPES_EXPORTED, epitopes, evidence_payload, funnel, manifest, panels


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Run the pipeline once on the offline fixture and export from it."""

    from neoag.config import load_settings
    from neoag.io.uniprot import parse_fasta
    from neoag.paths import Paths
    from neoag.pipeline import s1_fetch, s2_annotate, s3_peptides, s4_predict, s5_rank, s6_construct
    from neoag.pipeline.predictors.base import load_predictor

    paths = Paths()
    settings = load_settings([
        paths.root / "config" / "default.yaml", paths.root / "config" / "synthetic.yaml"
    ])
    proteome_fasta = parse_fasta((paths.fixtures / "synthetic_proteome.fasta").read_text())
    mutations = s1_fetch.run(settings, paths, None)
    annotations, proteome = s2_annotate.run(
        settings, paths, mutations, fixture_proteome=proteome_fasta
    )
    pairs = s3_peptides.run(settings, annotations, proteome)
    predictor = load_predictor("stub")
    predictions, _ = s4_predict.run(settings, pairs, predictor)
    rankings = {
        name: s5_rank.run(settings, pairs, predictions, annotations, name)
        for name in settings.hla.panels
    }
    construct = s6_construct.run(settings, rankings[settings.hla.primary_panel], predictor)
    return {
        "settings": settings, "mutations": mutations, "annotations": annotations,
        "rankings": rankings, "primary": rankings[settings.hla.primary_panel],
        "construct": construct, "predictor": predictor,
    }


class TestManifest:
    def test_labels_synthetic_data_as_not_real(self, built):
        m = manifest(built["settings"], built["mutations"], built["annotations"],
                     built["primary"], built["construct"], "stub-1")
        assert m["sample"]["is_real_tumour_data"] is False
        assert m["predictor"]["is_real_prediction"] is False

    def test_carries_the_hla_assumption(self, built):
        """The weakest assumption in the project must reach the page."""
        m = manifest(built["settings"], built["mutations"], built["annotations"],
                     built["primary"], built["construct"], "stub-1")
        assert "assumed, not measured" in m["hla"]["assumption"]

    def test_states_the_limitations(self, built):
        m = manifest(built["settings"], built["mutations"], built["annotations"],
                     built["primary"], built["construct"], "stub-1")
        joined = " ".join(m["limitations"]).lower()
        for expected in ("hla type is assumed", "matched normal", "immunogenicity"):
            assert expected in joined

    def test_build_date_does_not_churn_the_file(self):
        """A second-resolution timestamp would dirty site/data on every rebuild."""
        import json

        from neoag.paths import Paths

        committed = json.loads((Paths().root / "site" / "data" / "manifest.json").read_text())
        assert "generated_utc" not in committed
        assert len(committed["generated_date"]) == 10

    def test_disclaims_approval(self, built):
        m = manifest(built["settings"], built["mutations"], built["annotations"],
                     built["primary"], built["construct"], "stub-1")
        joined = " ".join(m["disclaimers"]).lower()
        assert "not approved by any regulator" in joined
        assert "not medical advice" in joined


class TestFunnel:
    def test_every_step_reports_what_it_discarded(self, built):
        steps = funnel(built["mutations"], built["annotations"], built["primary"])
        assert len(steps) == 4
        narrowing = [s for s in steps if s["n_out"] < s["n_in"]]
        assert narrowing, "at least one step should narrow"
        for step in narrowing:
            assert step["reasons"], f"{step['step']} discarded without saying why"

    def test_discard_counts_reconcile(self, built):
        """Reasons must account for everything dropped, or something vanished silently."""
        steps = funnel(built["mutations"], built["annotations"], built["primary"])
        final = steps[-1]
        assert sum(final["reasons"].values()) == final["n_in"] - final["n_out"]


class TestEpitopes:
    def test_all_selected_are_exported(self, built):
        """The limit may drop also-rans but must never drop a chosen one."""
        payload = epitopes(built["primary"], limit=40)
        selected = [e for e in payload["epitopes"] if e["sel"]]
        assert len(selected) == len(built["primary"].selected_ids)

    def test_respects_the_export_limit(self, built):
        payload = epitopes(built["primary"], limit=50)
        assert len(payload["epitopes"]) <= 50

    def test_every_candidate_says_why_it_lost(self, built):
        payload = epitopes(built["primary"])
        for e in payload["epitopes"]:
            assert e["sel"] or e["why_not"]

    def test_components_are_exported_for_live_reweighting(self, built):
        payload = epitopes(built["primary"])
        for e in payload["epitopes"][:20]:
            assert set(e["c"]) == {"presentation", "agretopicity", "expression", "quality"}

    def test_default_limit_is_sane(self):
        assert 100 <= MAX_EPITOPES_EXPORTED <= 2000


class TestPanels:
    def test_reports_overlap_between_hla_panels(self, built):
        payload = panels(built["rankings"])
        assert set(payload["panels"]) == set(built["settings"].hla.panels)
        assert "shared_by_all" in payload["overlap"]
        assert payload["overlap"]["pairwise"]

    def test_shared_count_cannot_exceed_a_panel(self, built):
        payload = panels(built["rankings"])
        smallest = min(len(p["selected"]) for p in payload["panels"].values())
        assert payload["overlap"]["shared_by_all"] <= smallest


@pytest.fixture(scope="module")
def ev():
    return evidence_payload()


class TestEvidencePayload:

    def test_contains_curves_for_both_arms(self, ev):
        for arm in ("combo", "control"):
            assert len(ev["curves"][arm]["t"]) == len(ev["curves"][arm]["s"])
            assert ev["curves"][arm]["n_risk"][0]["n"] in (107, 50)

    def test_validation_passes_and_is_published(self, ev):
        assert ev["validation"]["passed"] is True
        assert ev["validation"]["markdown"].startswith("| quantity |")

    def test_every_cut_records_whether_its_p_value_was_protected(self, ev):
        for cut in ev["cuts"]:
            assert "p_is_nominal" in cut
            assert cut["source"]

    def test_landmarks_carry_uncertainty_and_an_nnt_string(self, ev):
        for lm in ev["landmarks"]:
            assert lm["ci_low_per_100"] <= lm["per_100"] <= lm["ci_high_per_100"]
            assert lm["nnt"]

    def test_explainers_reach_the_page(self, ev):
        for key in ("one_sided_alpha", "open_label", "rfs_is_not_survival", "phase_3"):
            assert key in ev["explainers"]
            assert ev["explainers"][key]["plain"]

    def test_placement_sensitivity_is_published(self, ev):
        """The single assumption, and its influence, must be visible to a reader."""
        s = ev["reconstruction"]["placement_sensitivity"]
        assert len(s["hr_by_placement"]) == 4
        assert s["spread"] < 0.02

    def test_serialises_to_json(self, ev):
        assert json.loads(json.dumps(ev))
