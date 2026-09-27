PYTHON ?= python3.14
VENV := .venv
BIN := $(VENV)/bin

.PHONY: install lint format test data

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
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

test: install
	$(BIN)/pytest

data: install
	$(BIN)/python -m juriscope.ingest
