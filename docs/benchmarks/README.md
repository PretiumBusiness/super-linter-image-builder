# Benchmarks

Question: how much faster is a lean image than upstream `slim` on a cold runner,
and is that enough to justify this tool?

## Go / no-go

Go if the lean image for the first target (ghwm) pulls in about 20 s or less, or
is at least 3x faster than slim on a **GitHub-hosted** runner. Otherwise the
honest outcome is a "slim plus caching" write-up.

## When benchmarks run

Nothing runs on upstream's behalf unless upstream has a newer release than the
one pinned in `upstream-version.txt`:

1. The weekly `upstream-sync` run makes one API call. If the pin is current it
   stops there, with no checkout of upstream, no build and no benchmark.
2. If upstream is ahead it adds missing linters to the mapping, checks them with
   an all-linters image and opens a pull request that bumps the pin.
3. Merging that pull request runs the `release` workflow: it benchmarks the old
   version (only if no results are stored for it) and the new one with the same
   profiles, and publishes a GitHub release `upstream-<tag>` whose notes show
   the numbers before and after (`scripts/release_notes.py`).

Results are stored on the `bench-results` branch under `results/by-tag/<tag>/`.
The profiles used for releases come from the repository variable
`RELEASE_PROFILES` (default `ghwm,python,frontend-react,dotnet`). Starting the
`Toolchain benchmark` workflow by hand is still possible, as an explicit
decision, for example to add a profile to the stored results.

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

- Workflow: `.github/workflows/profiles.yml` (manual dispatch or called by the release workflow, one job per stack profile; runs on `ubuntu-latest` unless the `RUNNER_LABELS` repository variable or the `runner_labels` input says otherwise).
- Variants:
  - `slim`: `ghcr.io/super-linter/super-linter:slim-<tag>`
  - `lean-gzip`: `overlay/Dockerfile.ghwm`, default gzip layers
  - `lean-zstd`: same image, zstd-compressed layers
- Runners: `ubuntu-latest` (headline numbers) and optionally a self-hosted runner (repository variable `RUNNER_LABELS`), cold and warm (`BENCH_MODE`).
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

## What the benchmark covers

The tool is fully configurable, so the benchmark is only a set of example
combinations: the opinionated base plus one example toolchain each
(`toolchains/`), and the ghwm repository's exact flags (`examples/ghwm.env`).
There are no single-linter profiles on purpose: a repository that needs one
linter has no reason to use Super-Linter. `base-only` measures the base on its
own, as the floor for the toolchains.

## Results

Run 38144305432, upstream v9.0.0, a self-hosted runner (Proxmox VM,
2 CPU, 4 GB RAM, 40 GB disk), median of 3 cold pulls. Baseline is upstream
`slim-v9.0.0`. Every profile except `ghwm` is the shared base
(`base/opinionated.env`) plus its stack flags. Raw data is on the `bench-results`
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
| rust | 96.0 s | 16.9 s | 6.6 s | 7885 to 1540 MB (-80%) | 1798 to 376 MB (-79%) | 177 s |
| dotnet | 98.6 s | 15.1 s | 7.8 s | 7885 to 1555 MB (-80%) | 1798 to 378 MB (-79%) | 200 s |

Warm runner (image already present): pull is a no-op, about 1.5 s for the
baseline and 0.9 s for lean; container start 0.4 s vs 0.3 s. A smaller image
does not make a runner that already holds the full image meaningfully faster.

Baseline drift (first vs last cold pull) stayed within 5% on every profile.
Build time is gzip and zstd together; later runs record them separately.

dotnet and rust (run 38152523859, same runner) are compared against the upstream
`standard` image (`v9.0.0`), which is larger than slim: 7885 MB unpacked, 1798 MB
compressed. Their baseline drift was 2% and 13%. In that run the build time was
recorded per variant (gzip 167 s / zstd 32 s for dotnet, 141 s / 36 s for rust).
The zstd build runs second and reuses the build cache, so its time is not a
fair cold-build number.

### Every mapped linter at once

Run 38165304659 built an image with all 95 mapped flags (`all-linters`, based on
upstream `standard`) to verify the mapping: 80 tool checks ran and all tools
worked (the one reported failure was a false positive in the checker, fixed).
The lean image is 7037 MB unpacked and 1679 MB compressed against 7885 MB and
1798 MB for upstream standard, with a cold pull of 72.4 s (gzip) and 26.5 s
(zstd). With every linter enabled the size saving is only about 11%, as expected:
the saving comes from leaving linters out, so the tool pays off for repositories
that use a subset. The baseline pull of this run did not complete.

Open: GitHub-hosted
runner numbers (blocked by org billing), upgrade-pull scenario.
