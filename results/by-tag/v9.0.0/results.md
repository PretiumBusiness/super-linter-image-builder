## Lean vs upstream baseline (upstream v9.0.0)

### Cold pull (image removed before each pull)

| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base-only | 68.3 s | 8.7 s | 0.5 s | 7.8x | 139.4x | 3995 MB | 481 MB | 88% | 1310 MB | 150 MB | 89% | 1% | 83.2 s | 8.3 s |
| c-cpp | 66.8 s | 8.6 s | 0.4 s | 7.8x | 166.9x | 3995 MB | 497 MB | 88% | 1310 MB | 156 MB | 88% | -1% | 72.1 s | 18.7 s |
| dotnet | 78.5 s | 14.1 s | 0.3 s | 5.6x | 237.9x | 5585 MB | 1093 MB | 80% | 1798 MB | 378 MB | 79% | -0% | 104.3 s | 10.6 s |
| frontend-angular | 67.4 s | 8.8 s | 0.2 s | 7.7x | 280.8x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -1% | 70.2 s | 6.2 s |
| frontend-react | 83 s | 12.4 s | 0.7 s | 6.7x | 116.9x | 3995 MB | 512 MB | 87% | 1310 MB | 156 MB | 88% | -6% | 95.9 s | 8.7 s |
| frontend-svelte | 67.5 s | 9.4 s | 0.4 s | 7.2x | 160.7x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -0% | 71.9 s | 7.3 s |
| frontend-vanilla | 66.5 s | 8.3 s | 0.5 s | 8x | 138.6x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -3% | 69.3 s | 6.2 s |
| frontend-vue | 74.7 s | 9.7 s | 0.5 s | 7.7x | 166x | 3995 MB | 491 MB | 88% | 1310 MB | 152 MB | 88% | -1% | 75.5 s | 7.5 s |
| ghwm | 65.5 s | 9.2 s | 0.4 s | 7.1x | 152.2x | 3995 MB | 520 MB | 87% | 1310 MB | 170 MB | 87% | -4% | 71.5 s | 7.2 s |
| java | 74.5 s | 13.8 s | 0.6 s | 5.4x | 116.3x | 3995 MB | 698 MB | 83% | 1310 MB | 233 MB | 82% | -1% | 85.8 s | 9.5 s |
| python | 69.5 s | 12.6 s | 11.5 s | 5.5x | 6.1x | 3995 MB | 660 MB | 83% | 1310 MB | 210 MB | 84% | 0% | 87.8 s | 6.9 s |
| rust | 94.4 s | 22.9 s | 0.7 s | 4.1x | 136.8x | 5585 MB | 1091 MB | 80% | 1798 MB | 376 MB | 79% | 1% | 105 s | 18 s |

### Warm pull (image already on the runner) and container start

| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |
|---|---|---|---|---|
| base-only | 0.5 s | 0.5 s | 0.2 s | 0.2 s |
| c-cpp | 0.4 s | 0.4 s | 0.2 s | 0.2 s |
| dotnet | 0.3 s | 0.3 s | 0.2 s | 0.2 s |
| frontend-angular | 0.2 s | 0.2 s | 0.2 s | 0.2 s |
| frontend-react | 0.7 s | 0.7 s | 0.2 s | 0.2 s |
| frontend-svelte | 0.5 s | 0.4 s | 0.2 s | 0.2 s |
| frontend-vanilla | 0.5 s | 0.5 s | 0.2 s | 0.2 s |
| frontend-vue | 0.5 s | 0.4 s | 0.2 s | 0.2 s |
| ghwm | 0.4 s | 0.5 s | 0.2 s | 0.2 s |
| java | 0.6 s | 0.6 s | 0.2 s | 0.2 s |
| python | 0.3 s | 0.3 s | 0.2 s | 0.2 s |
| rust | 0.7 s | 0.7 s | 0.2 s | 0.2 s |
