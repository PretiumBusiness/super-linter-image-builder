## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all-linters | 87.4 s | 80.4 s | 78.1 s | 1.1x | 1.1x | 5585 MB | 5187 MB | 7% | 1798 MB | 1693 MB | 6% | -9% | 260.1 s | 45.2 s |
| ghwm | 69.3 s | 11.3 s | 10.6 s | 6.1x | 6.5x | 3995 MB | 520 MB | 87% | 1310 MB | 170 MB | 87% | 2% | 78.1 s | 8 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| all-linters | 0.7 s | 0.7 s | 0.2 s | 0.2 s |
| ghwm | 0.5 s | 0.5 s | 0.2 s | 0.2 s |
