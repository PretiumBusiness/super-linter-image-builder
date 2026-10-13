## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all-linters | 83.6 s | 82.7 s | 75 s | 1x | 1.1x | 5585 MB | 4901 MB | 12% | 1798 MB | 1679 MB | 7% | -1% | 231.2 s | 43.7 s |
| ghwm | 71.7 s | 11.7 s | 10.6 s | 6.1x | 6.8x | 3995 MB | 520 MB | 87% | 1310 MB | 170 MB | 87% | -2% | 81 s | 9.1 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| all-linters | 0.7 s | 0.6 s | 0.2 s | 0.2 s |
| ghwm | 0.4 s | 0.4 s | 0.2 s | 0.2 s |
