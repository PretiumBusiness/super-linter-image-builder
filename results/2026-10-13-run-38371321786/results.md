## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-only | 83.4 s | 10.7 s | 10.1 s | 7.8x | 8.3x | 3995 MB | 481 MB | 88% | 1310 MB | 150 MB | 89% | -2% | 82.5 s | 7.2 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| base-only | 0.5 s | 0.5 s | 0.2 s | 0.2 s |
