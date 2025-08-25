SHELL := /bin/zsh

.PHONY: setup format lint hooks cz bump

setup:
	uv pip install -r requirements.txt
	uv pip install --upgrade ruff black pre-commit commitizen
	pre-commit install
	pre-commit install -t commit-msg

format:
	uv run ruff format
	uv run ruff check --fix

lint:
	uv run ruff check

hooks:
	pre-commit run --all-files

cz:
	cz c

bump:
	cz bump --changelog
