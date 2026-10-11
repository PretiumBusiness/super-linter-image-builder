## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dotnet | 98.6 s | 15.1 s | 7.8 s | 6.5x | 12.6x | 7885 MB | 1555 MB | 80% | 1798 MB | 378 MB | 79% | 2% | 167.3 s | 32.4 s |
| rust | 96 s | 16.9 s | 6.6 s | 5.7x | 14.6x | 7885 MB | 1540 MB | 80% | 1798 MB | 376 MB | 79% | 13% | 141.1 s | 36.2 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| dotnet | 1.7 s | 0.9 s | 0.4 s | 0.3 s |
| rust | 1.7 s | 0.9 s | 0.4 s | 0.3 s |
