# "Your Tumor, Your Vaccine" -- reproducible build.
#
#   make setup      one-time: virtualenv, dependencies, prediction models
#   make all        rebuild every artifact
#   make synthetic  same, fully offline, no model download (what CI runs)
#   make test       the offline test suite
#
# Stages are incremental. Each depends on its input artifact, its own source
# modules, and a fingerprint of only the config it reads -- so editing a scoring
# weight rebuilds ranking onward without redoing the slow prediction stage.

PY       := .venv/bin/python
NEOAG    := $(PY) -m neoag
PYTHON311 ?= /opt/homebrew/bin/python3.11
# `make synthetic` is a config switch, not a recursive dispatch: recursing would
# re-parse this file with a different config and rewrite every stage fingerprint.
ifneq ($(filter synthetic,$(MAKECMDGOALS)),)
CONFIG   := config/default.yaml config/synthetic.yaml
endif
CONFIG   ?= config/default.yaml
CFGARGS  := $(foreach c,$(CONFIG),-c $(c))

I := data/interim
P := data/processed
S := build/stamps

# Deterministic output: no hash randomisation, no embedded timestamps, no GUI backend.
export PYTHONHASHSEED := 0
export SOURCE_DATE_EPOCH := 0
export MPLBACKEND := Agg
export MHCFLURRY_DOWNLOADS_DIR := $(CURDIR)/data/cache/mhcflurry
MHCFLURRY_RELEASE := 2.3.0

.PHONY: all synthetic setup models test test-network test-models lint typecheck figures-check \
        clean clean-interim distclean summary help

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | expand -t24

all: site/data/manifest.json figures/km_survival.png linkedin/carousel.pdf ## Rebuild every artifact

synthetic: site/data/manifest.json figures/km_survival.png ## Rebuild everything offline from the committed fixture

setup: ## Create the virtualenv and install everything
	$(PYTHON311) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev,predict,construct,video]"
	$(MAKE) models

models: ## Download the MHCflurry presentation models (~160 MB, one time)
	@mkdir -p data/cache/mhcflurry
	.venv/bin/mhcflurry downloads fetch models_class1_presentation --release $(MHCFLURRY_RELEASE)

# -- config fingerprints ---------------------------------------------------- #
# Refreshed at parse time, before make evaluates the dependency graph, and
# rewritten only when the config a stage actually reads has changed. Doing it
# here rather than as a rule keeps correctness independent of the config file's
# own timestamp -- restoring a backup or checking out an older revision moves a
# timestamp backwards, and a timestamp-based rule would then skip a rebuild that
# is genuinely needed.
STAMPS := $(shell $(NEOAG) $(CFGARGS) config-stamps --outdir $(S) 2>&1)
$(if $(STAMPS),$(info $(STAMPS)))

# -- stages ----------------------------------------------------------------- #
$(I)/01_mutations.json: $(S)/s1_fetch.json src/neoag/pipeline/s1_fetch.py src/neoag/io/cbioportal.py
	$(NEOAG) $(CFGARGS) fetch

$(I)/02_annotated.json: $(I)/01_mutations.json $(S)/s2_annotate.json \
                        src/neoag/pipeline/s2_annotate.py src/neoag/io/genome_nexus.py src/neoag/io/uniprot.py
	$(NEOAG) $(CFGARGS) annotate

$(I)/03_peptides.jsonl: $(I)/02_annotated.json $(S)/s3_peptides.json src/neoag/pipeline/s3_peptides.py
	$(NEOAG) $(CFGARGS) peptides

$(I)/04_predictions.parquet: $(I)/03_peptides.jsonl $(S)/s4_predict.json \
                             src/neoag/pipeline/s4_predict.py src/neoag/pipeline/predictors/*.py
	$(NEOAG) $(CFGARGS) predict

$(P)/05_ranked.json: $(I)/04_predictions.parquet $(S)/s5_rank.json \
                     src/neoag/pipeline/s5_rank.py src/neoag/pipeline/scoring.py src/neoag/pipeline/selection.py
	$(NEOAG) $(CFGARGS) rank

$(P)/06_construct.json: $(P)/05_ranked.json $(S)/s6_construct.json \
                        src/neoag/pipeline/s6_construct.py src/neoag/pipeline/construct/*.py
	$(NEOAG) $(CFGARGS) construct

# The website reads these directly; they are committed so GitHub Pages needs no build.
site/data/manifest.json: $(P)/06_construct.json src/neoag/export.py src/neoag/evidence/*.py
	$(NEOAG) $(CFGARGS) export

figures/km_survival.png: site/data/manifest.json src/neoag/figures/*.py
	$(NEOAG) $(CFGARGS) figures

linkedin/carousel.pdf: site/data/manifest.json src/neoag/figures/carousel.py
	$(NEOAG) $(CFGARGS) carousel

# Video is excluded from `make all`: ffmpeg embeds encoder metadata that cannot
# be fully suppressed, so the output is not byte-reproducible and is gitignored.
video: site/data/manifest.json ## Render the pipeline animation (needs ffmpeg)
	$(NEOAG) $(CFGARGS) animation

.PHONY: site evidence export video carousel
export: site/data/manifest.json ## Write the website's JSON payloads
figures: figures/km_survival.png ## Render the static PNG figures
carousel: linkedin/carousel.pdf ## Build the LinkedIn carousel PDF and slide PNGs

evidence: ## Reconstruct the trial data and print the validation table
	@$(NEOAG) evidence

site: site/data/manifest.json ## Serve the website locally
	@echo "serving http://127.0.0.1:8000 — ctrl-c to stop"
	@cd site && $(CURDIR)/$(PY) -m http.server 8000

summary: $(P)/06_construct.json ## Print a summary of the last run
	@$(NEOAG) $(CFGARGS) summary

# -- quality ---------------------------------------------------------------- #
test: ## Offline test suite: no network, no model download
	$(PY) -m pytest -q

test-network: ## Contract tests against the live public APIs
	$(PY) -m pytest -q -m network

test-models: ## Tests that need the MHCflurry models
	$(PY) -m pytest -q -m models

figures-check: ## Verify a figure rebuild is byte-identical to what is committed
	@tmp=$$(mktemp -d); $(NEOAG) $(CFGARGS) figures --outdir $$tmp >/dev/null; \
	 ok=1; for f in figures/*.png; do \
	   cmp -s "$$f" "$$tmp/$$(basename $$f)" || { echo "CHANGED: $$f"; ok=0; }; \
	 done; rm -rf $$tmp; \
	 [ $$ok -eq 1 ] && echo "all figures reproduce byte-for-byte"

lint:
	.venv/bin/ruff check src tests scripts

typecheck:
	.venv/bin/mypy src/neoag

# -- cleaning --------------------------------------------------------------- #
clean-interim: ## Remove generated artifacts, keep caches (fast offline rebuild)
	rm -rf $(I) $(P) $(S) out

clean: clean-interim

distclean: clean-interim ## Also remove the HTTP and model caches
	rm -rf data/cache
