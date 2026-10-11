## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c-cpp | 69.2 s | 9.8 s | 3.6 s | 7x | 19.2x | 5789 MB | 726 MB | 87% | 1310 MB | 156 MB | 88% | 5% |
| frontend-angular | 72.7 s | 8.9 s | 3.7 s | 8.2x | 19.5x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | -1% |
| frontend-react | 71.1 s | 9.7 s | 3.6 s | 7.3x | 19.6x | 5789 MB | 755 MB | 87% | 1310 MB | 156 MB | 88% | 0% |
| frontend-svelte | 71.9 s | 9.2 s | 4.1 s | 7.8x | 17.7x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | 5% |
| frontend-vanilla | 71.1 s | 9.4 s | 3.4 s | 7.6x | 21x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | 0% |
| frontend-vue | 71.3 s | 9.3 s | 3.6 s | 7.6x | 19.8x | 5789 MB | 722 MB | 88% | 1310 MB | 152 MB | 88% | 0% |
| ghwm | 75.6 s | 10.2 s | 4.6 s | 7.4x | 16.6x | 5789 MB | 771 MB | 87% | 1310 MB | 170 MB | 87% | -3% |
| java | 71.7 s | 13.2 s | 5.3 s | 5.4x | 13.5x | 5789 MB | 1004 MB | 83% | 1310 MB | 233 MB | 82% | -0% |
| python | 73.4 s | 12.4 s | 5.7 s | 5.9x | 12.9x | 5789 MB | 965 MB | 83% | 1310 MB | 210 MB | 84% | -2% |
| rust | n/a | 19.4 s | 15 s | n/a | n/a | n/a | 1540 MB | n/a | n/a | 376 MB | n/a | n/a |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| c-cpp | 1.3 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-angular | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-react | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-svelte | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-vanilla | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| frontend-vue | 1.4 s | 0.9 s | 0.4 s | 0.3 s |
| ghwm | 1.4 s | 0.9 s | 0.4 s | 0.3 s |
| java | 1.6 s | 0.9 s | 0.4 s | 0.4 s |
| python | 1.6 s | 0.9 s | 0.4 s | 0.3 s |
| rust | n/a | 0.9 s | n/a | 0.3 s |
