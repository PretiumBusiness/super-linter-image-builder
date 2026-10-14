## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all-linters | 80.8 s | 75.4 s | 68.1 s | 1.1x | 1.2x | 5585 MB | 5187 MB | 7% | 1798 MB | 1693 MB | 6% | 0% | 218.2 s | 32.7 s |
| ghwm | 70.2 s | 10.3 s | 9.2 s | 6.8x | 7.6x | 3995 MB | 520 MB | 87% | 1310 MB | 170 MB | 87% | -3% | 68.9 s | 6.1 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| all-linters | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
| ghwm | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
