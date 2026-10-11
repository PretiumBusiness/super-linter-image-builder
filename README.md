# super-linter-image-builder

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

## Layout

| Path | Purpose |
|---|---|
| `compiler/generate.py` | Profile (`VALIDATE_*` flags) -> Dockerfile, tool self-checks and plan |
| `compiler/linters.json` | Flag -> upstream paths, venvs, npm packages, apk packages |
| `compiler/prune-node-modules.js` | Copies only the dependency closure of the needed npm packages |
| `base/opinionated.env` | The opinionated base: the checks almost every repository wants (editorconfig, env, actionlint, zizmor, gitleaks, json, markdown, natural language, yaml, shell, hadolint) |
| `toolchains/` | Example toolchains on top of the base: python, java, dotnet, rust, c-cpp, frontend-{vanilla,react,vue,angular,svelte}, base-only |
| `examples/ghwm.env` | A real repository's exact flags, without the base |
| `sim/` | Pull-time simulation (estimates, runs without a registry) |
| `overlay/Dockerfile.ghwm` | The first hand-built overlay (kept for reference) |
| `examples/ghwm.env` | The ghwm Super-Linter environment, used as test input |
| `compiler/drift_check.py`, `compiler/filetypes.json` | PR drift blocker: fails when a PR adds files whose linters are not enabled (file-type rules transcribed from upstream) |
| `compiler/slconfig.py` | Reads the Super-Linter configuration from workflows and env files, with upstream's `VALIDATE_*` semantics |
| `.github/workflows/drift-blocker.yml` | Reusable workflow wrapping the drift check |
| `tests/` | Unit tests (`python3 -m unittest discover -s tests`), using the ghwm workflow as a fixture |
| `scripts/bench-pull.sh` | Cold pull timing |
| `scripts/summarize.sh` | Results table from benchmark output |
| `.github/workflows/profiles.yml` | Per profile: generate, push to GHCR, verify tools, benchmark cold and warm pulls (self-hosted runner) |
| `.github/workflows/benchmark.yml` | Earlier GitHub-hosted benchmark for the ghwm overlay |

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
    uses: PretiumBusiness/super-linter-image-builder/.github/workflows/drift-blocker.yml@main
    with:
      workflow: .github/workflows/linter.yml   # the workflow with the super-linter step
      allow_ext: "txt lock"                    # file types you deliberately do not lint
```

The configuration is read from the `env:` of the Super-Linter step, with the
upstream rules: if any `VALIDATE_X` is `true`, only those linters run; if only
`false` values are set, everything else runs. `FILTER_REGEX_INCLUDE` and
`FILTER_REGEX_EXCLUDE` are respected. The same discovery works in the compiler:
`generate.py --workflow .github/workflows/linter.yml ...`. Content-based
detections (OpenAPI, CloudFormation, Kubernetes, ARM, AWS States, Ansible) are
not modelled, so a YAML file of those kinds is only checked as plain YAML.

## Try it locally

```
python3 compiler/generate.py --env base/opinionated.env --env toolchains/python.env \
  --upstream-tag v9.0.0 --upstream-dockerfile <upstream Dockerfile at that tag> --out build/python
docker buildx build build/python -t lean-python
docker run --rm -v "$PWD/build/python/checks.sh:/checks.sh:ro" --entrypoint bash lean-python /checks.sh
```

Profiles marked as needing the upstream `standard` image (dotnet, rust) are
compared against `standard`, not `slim`. Upstream has no Svelte-specific linter,
so the Svelte profile covers the JS, TS, CSS and HTML around it.
