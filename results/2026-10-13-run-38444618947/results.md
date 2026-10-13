## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all-linters | 82.6 s | 81.4 s | 75.7 s | 1x | 1.1x | 5585 MB | 4901 MB | 12% | 1798 MB | 1679 MB | 7% | 0% | 237.9 s | 41.9 s |
| ghwm | 67.1 s | 10.2 s | 9.2 s | 6.6x | 7.3x | 3995 MB | 520 MB | 87% | 1310 MB | 170 MB | 87% | 1% | 71.3 s | 6.9 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| all-linters | 0.4 s | 0.4 s | 0.2 s | 0.2 s |
| ghwm | 0.4 s | 0.4 s | 0.2 s | 0.2 s |
