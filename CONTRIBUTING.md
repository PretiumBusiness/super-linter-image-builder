# Contributing to superlint-lean

Thank you for your interest in contributing to `superlint-lean`! This document
explains how to set up your environment, run the quality checks, write tests and
submit your contribution.

Before you begin, read the [Architecture documentation](docs/ARCHITECTURE.md) and
the [AI/Developer agent guide](AGENTS.md). Automated developer agents can find
pre-configured coding and testing standards under [.agents/skills/](.agents/skills/).

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Standards](#testing-standards)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful, welcoming
and inclusive environment. Please report unacceptable behavior to the maintainers.

## Prerequisites

1. **Python 3.12** or newer.
2. **[uv](https://docs.astral.sh/uv/)** to manage the environment.
3. **Node.js and npx** for prose linting of the documentation.
4. **Docker** (optional) for the container-based super-linter run.
5. **[APM](https://github.com/microsoft/apm)** (optional) to restore the agent skills.

---

## Development Setup

```sh
git clone https://github.com/PretiumBusiness/super-linter-image-builder.git
cd super-linter-image-builder
make install            # uv sync
make setup-precommit    # install the pre-commit hooks
apm install             # optional: restore .agents/skills
```

---

## Development Workflow

Use the [Makefile](Makefile) targets:

| Target | What it does |
| :--- | :--- |
| `make test` | pytest with coverage (keep it at 90% or higher). |
| `make lint` | Ruff check. |
| `make format` | Ruff formatter. |
| `make type-check` | mypy. |
| `make lang` / `make lang-fix` | textlint for the documentation. |
| `make precommit` | Run every pre-commit hook against all files. |
| `make super-linter` / `make super-linter-fix` | Run Super-Linter via Docker, without or with auto-fix. |
| `make build` | Build the sdist and wheel. |

The pre-commit hooks run `make super-linter-fix` and `make test` before each commit.

---

## Coding Standards

- Prefer small functions and plain data over hidden state; write explicit branching.
- Keep command-line parsing in each command's `main`; put behavior in the module that owns it ([config](src/superlint_lean/config.py), [generate](src/superlint_lean/generate.py), [drift](src/superlint_lean/drift.py), [mapping_sync](src/superlint_lean/mapping_sync.py), [release_notes](src/superlint_lean/release_notes.py)).
- Do not run bulk renames over source files: shell and Dockerfile text lives in strings.
- Keep the linter mapping complete: `superlint-lean sync-mapping` must report no missing flags for the pinned upstream version.
- Nothing that follows upstream may run unless upstream has a newer release.
- If you change public behavior, update the [readme](README.md), [docs/reference/cli.md](docs/reference/cli.md) and, where relevant, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Testing Standards

All tests live in [tests/](tests):

- **Arrange / Act / Assert**: structure each test in those three parts.
- **Naming**: `test_<feature>_should_<expected_behavior>_when_<state_under_test>`.
- **File alignment**: test `src/superlint_lean/drift.py` in `tests/test_drift.py`, and so on.
- **No network and no Docker**: use `tmp_path` and small fake upstream checkouts.
- **Edge cases**: include failure paths (invalid values, mixed `true`/`false`, missing files, unknown flags).

---

## Pull Request Process

External contributors fork the repository, then:

```sh
git remote add upstream https://github.com/PretiumBusiness/super-linter-image-builder.git
git checkout -b type/description
```

Open the pull request against `main`. The repository only allows squash merges,
so the **pull request title becomes the commit message** and must follow
conventional commits (`feat`, `fix`, `docs`, `test`, `ci`, `chore`, `refactor`).

### Branching conventions

- `feat/description` - new features
- `fix/description` - bug fixes
- `docs/description` - documentation
- `test/description` - tests
- `ci/description` - workflows and GitHub configuration
- `chore/description` - dependencies, tooling, refactorings

### Commit messages

Use conventional commit prefixes, for example:

- `feat: add a --report option to generate`
- `fix(generate): restore the symlink test in the generated Dockerfile`
- `docs: describe the repository settings`

### Submission checklist

```sh
make test && make lint && make type-check && make super-linter
make lang
```

1. All tests pass and coverage stays at 90% or higher.
2. mypy and Ruff report nothing.
3. Super-Linter and textlint report nothing.
4. `git status` lists only the intended files.
