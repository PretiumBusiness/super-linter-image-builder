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
- add Alpine packages with `--extra-apk curl`

The toolchains in this repository, and the numbers in
[docs/benchmarks](docs/benchmarks/README.md), are examples of combinations, not
the supported set.

The reason for an opinionated base is that a repository using one linter has no
use for Super-Linter. The value is in running a broad set of checks, so the base
is broad and each toolchain adds a stack on top.

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
