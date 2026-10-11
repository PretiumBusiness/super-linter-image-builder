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
| `overlay/Dockerfile.ghwm` | Hand-built overlay for the ghwm linter set (spike) |
| `examples/ghwm.env` | The ghwm Super-Linter environment, used as test input |
| `scripts/bench-pull.sh` | Cold pull timing |
| `scripts/summarize.sh` | Results table from benchmark output |
| `.github/workflows/benchmark.yml` | Builds the overlay and runs the benchmark and smoke test |
