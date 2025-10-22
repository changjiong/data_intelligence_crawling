PY ?= 3.11

.PHONY: setup run test add remove up clean

setup:
	uv python install $(PY)
	uv venv --python $(PY) .venv
	uv sync

run:
	uv run python src/pipeline.py --dry-run

test:
	uv run -m pytest

add:
	uv add $(PKG)

remove:
	uv remove $(PKG)

up:
	uv up

clean:
	rm -rf .venv
