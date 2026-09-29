PYTHON ?= python3.14
VENV := .venv
BIN := $(VENV)/bin

.PHONY: install lint format test data test-corpus eval annotate api

install: $(VENV)/.installed

$(VENV)/.installed: requirements.txt pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --quiet --disable-pip-version-check -r requirements.txt -e .
	$(BIN)/pre-commit install
	touch $@

lint: install
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format: install
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

test: install
	$(BIN)/pytest

data: install
	$(BIN)/python -m juriscope.ingest

test-corpus: data
	$(BIN)/pytest -m corpus

eval: data
	$(BIN)/python -m juriscope.eval.run_eval data/questions/eval.jsonl --split dev

annotate: data
	$(BIN)/python -m juriscope.evalset.annotate

# modèle affiné et ses vecteurs, publiés par le workflow finetune (torch en plus)
data/models/e5-small-ft:
	gh release download embeddings -p ft-passages.npz -p e5-small-ft.zip --dir data/index --clobber
	unzip -oq data/index/e5-small-ft.zip -d data/models
	$(BIN)/pip install --quiet --disable-pip-version-check -r requirements-embed.txt

api: data data/models/e5-small-ft
	$(BIN)/uvicorn juriscope.api:build_app --factory
