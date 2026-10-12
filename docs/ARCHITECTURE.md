# Architecture

## Overview

`superlint-lean` generates lean Super-Linter images and guards the pull requests
that would outgrow them. Every command starts from the same input: the
`VALIDATE_*` flags of a repository, resolved with upstream's semantics.

```text
env files / workflow (VALIDATE_*)
            │
            ▼
   config.effective_flags()
            │
   ┌────────┼───────────────────┐
   ▼        ▼                   ▼
generate   drift          mapping_sync
   │        │                   │
   ▼        ▼                   ▼
build      PR check         linters.json
context    (exit code)      (draft entries)
   │
   ▼
release_notes (benchmarks of two upstream versions)
```

## Modules

| Module | Responsibility |
| :--- | :--- |
| `cli.py` | Dispatches `generate`, `drift`, `sync-mapping` and `release-notes`; prints usage and the version. |
| `config.py` | Parses env files and workflows; `effective_flags` implements the upstream `VALIDATE_*` rules. |
| `generate.py` | Turns the selected flags plus `data/linters.json` into `Dockerfile`, `checks.sh`, `plan.json`. |
| `drift.py` | Maps changed files to flags with `data/filetypes.json` and reports files no enabled linter covers. |
| `mapping_sync.py` | Reads an upstream checkout and adds draft entries to `linters.json` for new flags. |
| `release_notes.py` | Compares `bench-*.jsonl` results of two upstream versions into Markdown release notes. |

## Data

- `linters.json` maps each upstream flag to what it needs: binaries, directories, virtualenvs, npm groups, apk packages, links, environment and tool checks. It must cover every flag of the version pinned in `upstream-version.txt`.
- `filetypes.json` holds the file-type rules transcribed from upstream, so `drift` can tell which linters would lint a file.

## Workflows

| Workflow | Purpose |
| :--- | :--- |
| `tests.yml` | Lint, type-check, test with coverage, build. |
| `linter.yml` | Super-Linter and the pre-commit hooks. |
| `pr-title-check.yml` | Conventional commit PR titles. |
| `auto-assign-pr.yml` | Assigns the author to new pull requests. |
| `upstream-sync.yml` | Detects a newer upstream release; only then syncs the mapping and opens a bump pull request. |
| `release.yml` | On a bump of the pin: benchmarks old and new versions and publishes a release. |
| `profiles.yml` | Reusable benchmark per stack profile. |
| `drift-blocker.yml` | Reusable workflow other repositories call to run `drift`. |

## Design principles

- Nothing that follows upstream runs unless upstream has a newer release.
- Everything stays configurable; the base and toolchains are examples.
- Untrusted input (changed files, workflows) is read, never executed.
