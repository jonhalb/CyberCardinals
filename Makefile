# One command reproduces the headline number from raw data:   make reproduce
export PYTHONPATH := src
export PYTHONHASHSEED := 0
PY ?= python
SEED ?= 0
SEEDS ?= 0 1 2 3 4 12345
QUICK ?= 0
QUICKFLAG := $(if $(filter 1,$(QUICK)),--quick,)

.PHONY: help data graphs stats baselines train evaluate compare reproduce seeds variant unit memcheck clean-checkout contribution

help:
	@echo "make reproduce [SEED=0] [QUICK=1]   data -> graphs -> stats -> baselines -> train -> evaluate -> compare"
	@echo "make data|graphs|stats|baselines|train|evaluate|compare   individual steps"
	@echo "make seeds     train + evaluate for SEEDS=$(SEEDS)"
	@echo "make variant   authors' variant ablation (link prediction)"
	@echo "make unit      unit tests    make memcheck   log memory    make contribution   refresh README table"

data:      ; $(PY) -m kairos_repro.data.download
graphs:    ; $(PY) -m kairos_repro.data.build_graphs
stats:     ; $(PY) -m kairos_repro.data.stats

baselines:
	@test -f results/graph_features.csv || $(MAKE) stats
	$(PY) -m kairos_repro.baselines.do_nothing
	$(PY) -m kairos_repro.baselines.histogram_distance
	$(PY) -m kairos_repro.eval.compare --run results/baselines/do_nothing --seed 0 --name "Baseline B0: do nothing"
	$(PY) -m kairos_repro.eval.compare --run results/baselines/histogram_distance --seed 0 --name "Baseline B1: histogram distance"

train:     ; $(PY) -m kairos_repro.model.train --config configs/paper_faithful.json --seed $(SEED) $(QUICKFLAG)
evaluate:  ; $(PY) -m kairos_repro.model.evaluate --config configs/paper_faithful.json --seed $(SEED)
compare:   ; $(PY) -m kairos_repro.eval.compare --run results/paper_faithful --seed $(SEED) --name "Paper-faithful (ours)"

reproduce: data graphs stats baselines train evaluate compare
	@echo "headline:" && $(PY) -m kairos_repro.eval.check_headline --run results/paper_faithful --seed $(SEED)

seeds:
	for s in $(SEEDS); do $(MAKE) train evaluate compare SEED=$$s || exit 1; done

variant:
	$(PY) -m kairos_repro.model.train --config configs/authors_variant.json --seed $(SEED)
	$(PY) -m kairos_repro.model.evaluate --config configs/authors_variant.json --seed $(SEED)
	$(PY) -m kairos_repro.eval.compare --run results/authors_variant --seed $(SEED) --name "Authors' variant (ablation)"

unit:      ; $(PY) -m pytest -q
memcheck:  ; $(PY) -m kairos_repro.tools.memcheck
contribution: ; $(PY) scripts/contribution_table.py --git --write-readme README.md
clean-checkout: ; bash scripts/clean_checkout_test.sh
