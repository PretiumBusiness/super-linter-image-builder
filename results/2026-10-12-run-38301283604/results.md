## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python | 69.5 s | 12.6 s | 11.5 s | 5.5x | 6.1x | 3995 MB | 660 MB | 83% | 1310 MB | 210 MB | 84% | 0% | 87.8 s | 6.9 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| python | 0.3 s | 0.3 s | 0.2 s | 0.2 s |
