## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-only | 68.3 s | 9.4 s | 9.3 s | 7.3x | 7.4x | 3995 MB | 481 MB | 88% | 1310 MB | 150 MB | 89% | -3% | 69.5 s | 6.5 s |
| c-cpp | 77.6 s | 11 s | 10.5 s | 7.1x | 7.4x | 3995 MB | 497 MB | 88% | 1310 MB | 156 MB | 88% | 2% | 79.8 s | 5.3 s |
| dotnet | 91 s | 17 s | 15.4 s | 5.4x | 5.9x | 5585 MB | 1093 MB | 80% | 1798 MB | 378 MB | 79% | 6% | 116.9 s | 9.9 s |
| frontend-angular | 68.7 s | 9.5 s | 8.8 s | 7.2x | 7.8x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | 0% | 69.9 s | 5.7 s |
| frontend-react | 68.7 s | 10.4 s | 9.5 s | 6.6x | 7.3x | 3995 MB | 512 MB | 87% | 1310 MB | 156 MB | 88% | -1% | 70 s | 5.7 s |
| frontend-svelte | 68.5 s | 9.6 s | 8.7 s | 7.2x | 7.9x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -0% | 69 s | 6.3 s |
| frontend-vanilla | 68.3 s | 9.8 s | 8.6 s | 7x | 8x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -4% | 73.3 s | 6.1 s |
| frontend-vue | 68.3 s | 9.5 s | 8.7 s | 7.2x | 7.8x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -1% | 70.4 s | 6 s |
| ghwm | 70.7 s | 10.7 s | 9.8 s | 6.6x | 7.2x | 3995 MB | 520 MB | 87% | 1310 MB | 170 MB | 87% | -1% | 74.6 s | 7.3 s |
| java | 68.3 s | 10.7 s | 9.7 s | 6.4x | 7x | 3995 MB | 698 MB | 83% | 1310 MB | 233 MB | 82% | 0% | 75.6 s | 7.1 s |
| python | 67.9 s | 11.6 s | 11.5 s | 5.9x | 5.9x | 3995 MB | 660 MB | 83% | 1310 MB | 210 MB | 84% | -9% | 75.2 s | 6.6 s |
| rust | 81.2 s | 14.1 s | 14.3 s | 5.8x | 5.7x | 5585 MB | 1091 MB | 80% | 1798 MB | 376 MB | 79% | -0% | 93.1 s | 11.5 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| base-only | 0.5 s | 0.5 s | 0.4 s | 0.2 s |
| c-cpp | 0.2 s | 0.3 s | 0.3 s | 0.4 s |
| dotnet | 0.4 s | 0.4 s | 0.2 s | 0.2 s |
| frontend-angular | 0.3 s | 0.3 s | 0.2 s | 0.2 s |
| frontend-react | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
| frontend-svelte | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
| frontend-vanilla | 0.5 s | 0.5 s | 0.2 s | 0.2 s |
| frontend-vue | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
| ghwm | 0.4 s | 0.4 s | 0.2 s | 0.2 s |
| java | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
| python | 0.5 s | 0.4 s | 0.2 s | 0.2 s |
| rust | 0.3 s | 0.2 s | 0.2 s | 0.2 s |
