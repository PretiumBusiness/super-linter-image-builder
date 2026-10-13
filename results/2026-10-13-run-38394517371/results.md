## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-only | 68.3 s | 9.4 s | 9.3 s | 7.3x | 7.4x | 3995 MB | 481 MB | 88% | 1310 MB | 150 MB | 89% | -3% | 69.5 s | 6.5 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| base-only | 0.5 s | 0.5 s | 0.4 s | 0.2 s |
