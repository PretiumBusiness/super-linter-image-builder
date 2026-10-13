## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-only | 88 s | 11.7 s | 11.1 s | 7.5x | 7.9x | 3995 MB | 481 MB | 88% | 1310 MB | 150 MB | 89% | -2% | 91.2 s | 8.1 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| base-only | 0.8 s | 0.8 s | 0.4 s | 0.7 s |
