## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c-cpp | 69.2 s | 9.8 s | 3.6 s | 7x | 19.2x | 5789 MB | 726 MB | 87% | 1310 MB | 156 MB | 88% | 5% | n/a | n/a |
| dotnet | 98.6 s | 15.1 s | 7.8 s | 6.5x | 12.6x | 7885 MB | 1555 MB | 80% | 1798 MB | 378 MB | 79% | 2% | 167.3 s | 32.4 s |
| frontend-angular | 72.7 s | 8.9 s | 3.7 s | 8.2x | 19.5x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | -1% | n/a | n/a |
| frontend-react | 71.1 s | 9.7 s | 3.6 s | 7.3x | 19.6x | 5789 MB | 755 MB | 87% | 1310 MB | 156 MB | 88% | 0% | n/a | n/a |
| frontend-svelte | 71.9 s | 9.2 s | 4.1 s | 7.8x | 17.7x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | 5% | n/a | n/a |
| frontend-vanilla | 71.1 s | 9.4 s | 3.4 s | 7.6x | 21x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | 0% | n/a | n/a |
| frontend-vue | 71.3 s | 9.3 s | 3.6 s | 7.6x | 19.8x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | 0% | n/a | n/a |
| ghwm | 75.6 s | 10.2 s | 4.6 s | 7.4x | 16.6x | 5789 MB | 771 MB | 87% | 1310 MB | 170 MB | 87% | -3% | n/a | n/a |
| java | 71.7 s | 13.2 s | 5.3 s | 5.4x | 13.5x | 5789 MB | 1004 MB | 83% | 1310 MB | 233 MB | 82% | -0% | n/a | n/a |
| python | 73.4 s | 12.4 s | 5.7 s | 5.9x | 12.9x | 5789 MB | 965 MB | 83% | 1310 MB | 210 MB | 84% | -2% | n/a | n/a |
| rust | 96 s | 16.9 s | 6.6 s | 5.7x | 14.6x | 7885 MB | 1540 MB | 80% | 1798 MB | 376 MB | 79% | 13% | 141.1 s | 36.2 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| c-cpp | 1.3 s | 0.9 s | 0.4 s | 0.3 s |
| dotnet | 1.7 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-angular | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-react | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-svelte | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-vanilla | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-vue | 1.4 s | 0.9 s | 0.4 s | 0.3 s |
| ghwm | 1.4 s | 0.9 s | 0.4 s | 0.3 s |
| java | 1.6 s | 0.9 s | 0.4 s | 0.4 s |
| python | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| rust | 1.7 s | 0.9 s | 0.4 s | 0.3 s |
