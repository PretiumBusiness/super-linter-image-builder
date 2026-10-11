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

- Workflow: `.github/workflows/profiles.yml` (manual dispatch, self-hosted runner, one job per stack profile). `benchmark.yml` is the earlier GitHub-hosted version for ghwm only.
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

Run 38144305432, upstream v9.0.0, runner `[self-hosted, pretium]` (Proxmox VM,
2 CPU, 4 GB RAM, 40 GB disk), median of 3 cold pulls. Baseline is upstream
`slim-v9.0.0`. Every profile except `ghwm` is the shared base
(`profiles/common.env`) plus its stack flags. Raw data is on the `bench-results`
branch under `results/2026-10-11-run-38144305432/`.

| Profile | Baseline pull | Lean gzip | Lean zstd | Unpacked: base to lean | Compressed: base to lean | Build gzip+zstd (incl. push) |
|---|---|---|---|---|---|---|
| ghwm | 75.6 s | 10.2 s | 4.6 s | 5789 to 771 MB (-87%) | 1310 to 170 MB (-87%) | 129 s |
| python | 73.4 s | 12.4 s | 5.7 s | 5789 to 965 MB (-83%) | 1310 to 210 MB (-84%) | 153 s |
| java | 71.7 s | 13.2 s | 5.3 s | 5789 to 1004 MB (-83%) | 1310 to 233 MB (-82%) | 182 s |
| c-cpp | 69.2 s | 9.8 s | 3.6 s | 5789 to 726 MB (-87%) | 1310 to 156 MB (-88%) | 124 s |
| frontend-vanilla | 71.1 s | 9.4 s | 3.4 s | 5789 to 722 MB (-88%) | 1310 to 152 MB (-88%) | 128 s |
| frontend-react | 71.1 s | 9.7 s | 3.6 s | 5789 to 755 MB (-87%) | 1310 to 156 MB (-88%) | 133 s |
| frontend-vue | 71.3 s | 9.3 s | 3.6 s | 5789 to 722 MB (-88%) | 1310 to 152 MB (-88%) | 130 s |
| frontend-angular | 72.7 s | 8.9 s | 3.7 s | 5789 to 722 MB (-88%) | 1310 to 152 MB (-88%) | 135 s |
| frontend-svelte | 71.9 s | 9.2 s | 4.1 s | 5789 to 722 MB (-88%) | 1310 to 152 MB (-88%) | 139 s |
| rust | no valid baseline (tag bug, fixed) | 19.4 s | 15 s | 1540 MB lean | 376 MB lean | 232 s |
| dotnet | build failed (tag bug, then runner out of disk) | | | | | |

Warm runner (image already present): pull is a no-op, about 1.5 s for the
baseline and 0.9 s for lean; container start 0.4 s vs 0.3 s. A smaller image
does not make a runner that already holds the full image meaningfully faster.

Baseline drift (first vs last cold pull) stayed within 5% on every profile.
Build time is gzip and zstd together; later runs record them separately.

Open: dotnet and rust re-run with the corrected standard tag, GitHub-hosted
runner numbers (blocked by org billing), upgrade-pull scenario.
