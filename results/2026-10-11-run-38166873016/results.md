## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| extras-example | 72.8 s | 9.1 s | 4.6 s | 8x | 15.9x | 5789 MB | 723 MB | 88% | 1310 MB | 155 MB | 88% | 0% | 118.8 s | 16.6 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| extras-example | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
