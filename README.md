# superlint-lean

Generate lean, pinned [Super-Linter](https://github.com/super-linter/super-linter)
images that contain only the linters a repository uses, to cut the cold
pull-and-unpack time in CI.

Status: early. The first step is measuring whether this is worth building. See
[docs/benchmarks](docs/benchmarks/README.md) and the open issues.

## Idea

1. A repository declares the linters it needs, or they are discovered from the
   `VALIDATE_*` flags in its Super-Linter workflow.
2. A compiler builds an overlay image: same Python/Alpine base as upstream, plus
   only the needed tool paths copied from the upstream release image.
3. A PR check fails when a change adds file types the current image does not
   cover.
4. A scheduled job rebuilds when upstream publishes a new release.
5. The workflows are distributed through the ghwm registry.

## Install

The CLI is a Python package, managed with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install superlint-lean            # once it is published to PyPI
uvx --from git+https://github.com/ghwfxlab/superlint-lean superlint-lean --help
```

Commands:

| Command | Purpose |
| --- | --- |
| `superlint-lean generate` | `VALIDATE_*` flags (env files or a workflow) -> Dockerfile, tool self-checks and plan |
| `superlint-lean drift` | PR drift check: fails when changed files are not covered by the enabled linters |
| `superlint-lean sync-mapping` | Compare the linter mapping with an upstream checkout and add draft entries |
| `superlint-lean release-notes` | Release notes with before/after benchmarks of two upstream versions |

## Layout

| Path | Purpose |
| --- | --- |
| `src/superlint_lean/` | The package: `cli.py`, `generate.py`, `drift.py`, `config.py` (reads workflows and env files with upstream's `VALIDATE_*` semantics), `mapping_sync.py`, `release_notes.py` |
| `src/superlint_lean/data/` | `linters.json` (flag -> upstream paths, venvs, npm and apk packages), `filetypes.json` (file type rules transcribed from upstream), `prune-node-modules.js` |
| `tests/` | pytest suite (Arrange/Act/Assert), using the ghwm workflow as a fixture |
| `base/opinionated.env` | The opinionated base: the checks almost every repository wants (EditorConfig, env, actionlint, zizmor, gitleaks, JSON, Markdown, natural language, YAML, shell, hadolint) |
| `toolchains/` | Example toolchains on top of the base: python, Java, dotnet, rust, c-cpp, frontend-{vanilla,react,vue,angular,svelte}, base-only |
| `examples/` | `ghwm.env` (a real repository's exact flags, without the base) and `with-extras.env` |
| `scripts/` | `bench-pull.sh`, `compare.sh`, `summarize.sh`: cold pull timing and result tables |
| `.github/workflows/` | `tests`, `profiles` (benchmarks), `upstream-sync`, `release`, and the reusable `drift-blocker` |

## Development

```sh
make install          # uv sync
make setup-precommit  # pre-commit hooks (super-linter and the tests)
make test             # pytest with coverage
make lint             # ruff
make type-check       # mypy
make lang             # textlint for the docs
make super-linter     # super-linter via Docker
make build            # sdist and wheel
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, [AGENTS.md](AGENTS.md)
for the guide used by coding agents, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
and [docs/reference/cli.md](docs/reference/cli.md) for the internals and the
command reference, and [docs/repository-settings.md](docs/repository-settings.md)
for the repository settings. Report vulnerabilities as described in
[SECURITY.md](SECURITY.md).

## Configuration

Nothing is fixed. The base and the toolchains are plain env files with
`VALIDATE_*=true` lines, and the generator takes any combination of them:

- leave the base out, or write your own
- stack several toolchains (`--env toolchains/python.env --env toolchains/rust.env`)
- drop single linters from a combination with `--exclude NATURAL_LANGUAGE`
- add tools Super-Linter does not ship: Alpine packages (`--extra-apk`), npm
  packages (`--extra-npm`) and pip packages (`--extra-pip`), plus `--extra-check`
  commands that must succeed in the built image. They can also be written in an
  env file (`EXTRA_APK=`, `EXTRA_NPM=`, `EXTRA_PIP=`, `EXTRA_CHECK=`), see
  `examples/with-extras.env`. Extras are installed at build time from the
  package registries, in their own layers (`/opt/extras`), and npm installs run
  with `--ignore-scripts`

The toolchains in this repository, and the numbers in
[docs/benchmarks](docs/benchmarks/README.md), are examples of combinations, not
the supported set.

The reason for an opinionated base is that a repository using one linter has no
use for Super-Linter. The value is in running a broad set of checks, so the base
is broad and each toolchain adds a stack on top.

## Block pull requests that outgrow the image

The image only contains the linters you enabled. If a pull request adds a file
type whose linters are not enabled (a `.rs` file when no Rust linter is on),
Super-Linter would silently skip it. The drift blocker fails that pull request
and says which linter to enable:

```yaml
jobs:
  drift:
    permissions:
      contents: read
    uses: ghwfxlab/superlint-lean/.github/workflows/drift-blocker.yml@main
    with:
      workflow: .github/workflows/super-linter.yaml   # the workflow with the super-linter step
      allow_ext: "txt lock"                    # file types you deliberately do not lint
```

The configuration is read from the `env:` of the Super-Linter step, with the
upstream rules: if any `VALIDATE_X` is `true`, only those linters run; if only
`false` values are set, everything else runs. `FILTER_REGEX_INCLUDE` and
`FILTER_REGEX_EXCLUDE` are respected. The same discovery works in the compiler:
`superlint-lean generate --workflow .github/workflows/super-linter.yaml ...`. Content-based
detections (OpenAPI, CloudFormation, Kubernetes, ARM, AWS States, Ansible) are
not modelled, so a YAML file of those kinds is only checked as plain YAML.

## Try it locally

```sh
superlint-lean generate --env base/opinionated.env --env toolchains/python.env \
  --upstream-tag v9.0.0 --upstream-dockerfile <upstream Dockerfile at that tag> --out build/python
docker buildx build build/python -t lean-python
docker run --rm -v "$PWD/build/python/checks.sh:/checks.sh:ro" --entrypoint bash lean-python /checks.sh
```

Profiles marked as needing the upstream `standard` image (dotnet, rust) are
compared against `standard`, not `slim`. Upstream has no Svelte-specific linter,
so the Svelte profile covers the JS, TS, CSS and HTML around it.
