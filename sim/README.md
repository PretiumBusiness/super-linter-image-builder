# Pull-time simulation

A Monte Carlo model of cold `docker pull` time. It exists to answer "is this
worth building?" before the real benchmark has run. It is a prediction with
error bars, not a measurement.

## How it works

- Layers download up to 3 at a time (Docker's default), each stream capped by a
  per-connection rate and a shared bandwidth limit, then extract strictly in
  order. Extraction cost is unpacked MB / decompress speed + MB / disk write
  speed + files x per-file cost.
- Component sizes come from `components.json`. **They are estimates** of the
  upstream v9.0.0 slim contents, not measurements.
- Environment parameters (bandwidth, decompress speed, per-file cost, ...) are
  drawn from priors. Only draws where the simulated **slim** pull lands in the
  range you observe (default 60-90 s) are kept, so the unknowns are pinned to
  your real number.

```text
python3 sim/pull_model.py                      # default 60-90 s observed
python3 sim/pull_model.py --observed 50 70
python3 sim/pull_model.py --bandwidth 8 30 --per-conn 3 12 --per-file 5 20   # download-bound world
python3 sim/pull_model.py --bandwidth 150 400 --per-conn 40 150 --per-file 40 150  # unpack-bound world
```

## Result (estimated components, slim observed at 60-90 s)

| Variant | Pull median (p10-p90) | vs slim | Compressed | Unpacked |
| --- | --- | --- | --- | --- |
| slim | 74 s (63-86) | 1.0x | 1.7 GB | 5.2 GB |
| lean, whole `/node_modules` (as committed) | 25 s (20-33) | 3.0x | 0.4 GB | 1.5 GB |
| lean, pruned `/node_modules` | 10 s (9-13) | 7x | 0.2 GB | 0.6 GB |
| lean, pruned, zstd layers | 8 s (6-10) | 10x | 0.2 GB | 0.6 GB |
| illustrative polyglot repository, pruned | 22 s (18-25) | 3.5x | 0.5 GB | 1.5 GB |

Download-bound and unpack-bound worlds give the same ordering: whole-npm lean
2.4-3.1x, pruned 6.5-7.4x, pruned+zstd 8-10x.

## What drives the result

- Unpacked size and file count matter more than compressed size. Unpacking is
  80-95% of the simulated slim pull in most draws. The npm tree and the Python
  venvs are the file-count heavy parts.
- Pruning `/node_modules` is the biggest single lever after dropping the
  language runtimes, and also the least certain estimate here.
- zstd only helps if the runner's Docker pulls zstd layers efficiently. That
  is a hypothesis for the real benchmark to check.

## Not modelled

- A self-hosted runner that already holds the image: the pull is a manifest
  check of a second or two for every variant, so size barely matters. Measure it
  with `BENCH_MODE=warm` (see the benchmark workflow).
- Upgrade pulls (previous tag present, new tag pulled), image start time, and
  registry-side throttling.

## Replacing estimates with real data

```text
sim/profile-image.sh ghcr.io/super-linter/super-linter:slim-v9.0.0 layers-slim.json
sim/profile-image.sh <lean image> layers-lean.json
python3 sim/pull_model.py --measured slim=layers-slim.json lean=layers-lean.json
```
