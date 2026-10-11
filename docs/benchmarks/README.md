# Benchmarks

Question: how much faster is a lean image than upstream `slim` on a cold runner,
and is that enough to justify this tool?

## Go / no-go

Go if the lean image for the first target (ghwm) pulls in about 20 s or less, or
is at least 3x faster than slim on a **GitHub-hosted** runner. Otherwise the
honest outcome is a "slim plus caching" write-up.

## Pipeline under test

config -> create image -> push to GHCR -> pull on a runner. Today the "create
image" step is the hand-built `overlay/Dockerfile.ghwm`; it will be replaced by
the generated Dockerfile once the compiler exists (issues #3 to #5). Each
scenario compares upstream slim ("without") with the generated lean image
("with").

## Scenarios

1. **Cold, GitHub-hosted runner.** Headline number: what most users pay.
2. **Cold, self-hosted runner.** Image removed before each pull.
3. **Warm, self-hosted runner with the full image preloaded.** Tests whether a
   smaller image helps when nothing has to be downloaded. Expect little change
   in pull time; start time and disk use are the other things to look at.
4. **Upgrade pull** (not yet automated): previous upstream tag present, pull the
   next. Needs a second build.

A simulation (`sim/`) predicts scenario 1 before real numbers exist.

## Method

- Workflow: `.github/workflows/benchmark.yml` (manual dispatch).
- Variants:
  - `slim`: `ghcr.io/super-linter/super-linter:slim-<tag>`
  - `lean-gzip`: `overlay/Dockerfile.ghwm`, default gzip layers
  - `lean-zstd`: same image, zstd-compressed layers
- Runners: `ubuntu-latest` (headline numbers) and `[self-hosted, pretium]`, cold and warm (`BENCH_MODE`).
- Each run removes the image locally, then times `docker pull`. With `crane`
  available it also records a download-only pull and a `docker load`, giving a
  rough download vs unpack split.
- Median of N runs (default 5). Sizes are compressed layer size and
  uncompressed image size.

Self-hosted numbers are secondary. Runners that keep layers between jobs, or
that sit close to the registry, will make every variant look faster than most
users will see.

## Caveats

- The lean image is hand-built and still ships the whole `/node_modules` tree.
- `/action/linterVersions.txt` lists all upstream tools, not only the kept ones.
- Whether the Docker version on a hosted runner pulls zstd layers efficiently
  is one of the things this benchmark checks.

## Results

Fill in from the `results` artifact of a benchmark run.

| Date | Upstream | Runner | Variant | Pull median | Compressed | Uncompressed |
|---|---|---|---|---|---|---|
| | | | | | | |
