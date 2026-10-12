# AGENTS.md

## Purpose

`superlint-lean` is a Python CLI that generates lean, pinned Super-Linter images
from `VALIDATE_*` flags, blocks pull requests that outgrow the image, and keeps
its linter mapping in step with upstream Super-Linter releases.

## Repository layout

- `src/superlint_lean/cli.py` - entry point that dispatches the sub-commands
- `src/superlint_lean/generate.py` - flags -> Dockerfile, checks.sh, plan.json
- `src/superlint_lean/drift.py` - PR drift check (changed files vs enabled linters)
- `src/superlint_lean/config.py` - reads env files and workflows; upstream `VALIDATE_*` semantics
- `src/superlint_lean/mapping_sync.py` - adds draft mapping entries for new upstream linters
- `src/superlint_lean/release_notes.py` - before/after benchmark release notes
- `src/superlint_lean/data/` - `linters.json`, `filetypes.json`, `prune-node-modules.js`
- `base/`, `toolchains/`, `examples/` - env files (the opinionated base and example combinations)
- `scripts/` - benchmark shell scripts used by the workflows
- `tests/` - pytest suite
- `upstream-version.txt` - the pinned upstream Super-Linter release

## Development commands

- `make install` - sync dependencies with `uv`
- `make test` - pytest with coverage
- `make lint` - ruff
- `make type-check` - mypy
- `make build` - build sdist and wheel

## Rules

- Nothing that follows upstream may run unless upstream has a newer release (see `.github/workflows/upstream-sync.yml`).
- Everything stays configurable: the base and toolchains are examples, not the supported set.
- Keep the mapping complete: `superlint-lean sync-mapping` must report no missing flags for the pinned upstream version.
