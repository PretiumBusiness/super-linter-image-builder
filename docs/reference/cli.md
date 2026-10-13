# CLI Reference

```text
superlint-lean <command> [options]
superlint-lean --version
```

Run `superlint-lean <command> --help` for the full option list of a command.

## `generate`

Generate a lean image build context from `VALIDATE_*` flags.

| Option | Description |
| :--- | :--- |
| `--env FILE` | Env file with `VALIDATE_*=true` lines (repeatable). |
| `--workflow FILE` | Read the flags from the Super-Linter step of a workflow (repeatable). |
| `--all` | Select every flag in the mapping. |
| `--exclude FLAG` | Drop a flag, with or without the `VALIDATE_` prefix (repeatable). |
| `--extra-apk`, `--extra-npm`, `--extra-pip` | Extra packages installed at build time (repeatable). |
| `--extra-check CMD` | Command that must succeed in the built image (repeatable). |
| `--upstream-tag TAG` | Upstream release, for example `v9.0.0` (required). |
| `--upstream-dockerfile FILE` | The upstream Dockerfile at that tag (required). |
| `--out DIR` | Output directory (required). |
| `--mapping FILE` | Mapping to use instead of the bundled `linters.json`. |

Writes `Dockerfile`, `prune-node-modules.js`, `checks.sh` and `plan.json` to
`--out` and prints the upstream baseline variant (`slim` or `standard`).

## `drift`

Fail when changed files are not covered by the configured linters.

| Option | Description |
| :--- | :--- |
| `--workflow FILE`, `--env FILE` | Where the configuration comes from (repeatable). |
| `--base REF` | Diff against this Git ref. |
| `--files-from FILE` | File with one changed path per line. |
| `--root DIR` | Repository root (default: current directory). |
| `--allow-ext EXT` | Extension or filename you deliberately do not lint (repeatable). |
| `--warn-only` | Report but exit `0`. |
| `--report FILE` | Write a Markdown report. |

Exit codes: `0` all covered, `1` uncovered files, `2` configuration error.

## `sync-mapping`

Compare the bundled mapping with an upstream checkout and add draft entries.

| Option | Description |
| :--- | :--- |
| `--upstream DIR` | Upstream Super-Linter checkout (required). |
| `--write` | Add draft entries to the mapping file. |
| `--report FILE` | Write a Markdown report. |
| `--mapping FILE` | Mapping to update instead of the bundled one. |

Exit codes: `0` nothing missing, `10` drafts were added or flags need a manual mapping.

## `release-notes`

Write release notes comparing the benchmarks of two upstream versions.

| Option | Description |
| :--- | :--- |
| `--old-tag`, `--old-dir` | Previous upstream tag and its `bench-*.jsonl` directory (required). |
| `--new-tag`, `--new-dir` | New upstream tag and its results directory (required). |
| `--profiles A,B` | Limit the comparison to these profiles. |
| `--mapping-diff FILE` | Append the mapping changes between the versions. |
| `--out FILE` | Also write the notes to a file. |

## `compare`

Markdown tables from benchmark results: lean against the upstream baseline, per profile.

```text
superlint-lean compare FILE.jsonl...
```

Reads the `bench-*.jsonl` and `build-*.jsonl` files written by the benchmark workflow (one run per line, `variant`
is `<profile>/<kind>`). Prints a cold-pull table (median pull time, speedup, sizes, baseline drift, build time) and a
warm-pull table. Percentages round half away from zero, so a small negative change prints as `-0%`; a baseline drift
above 15% is marked `WARN`.

Exit codes: `0` printed, `2` no file given or a file could not be read.

## `summarize`

One row per runner, mode and variant, with the median and the range of the runs.

```text
superlint-lean summarize FILE.jsonl...
```

Same input and exit codes as `compare`. Rows without a runner (the build timings) print `null` and come first.

## `repository-settings`

Print or apply the repository settings in [repository-settings.md](../repository-settings.md). Maintainer tooling.

```text
superlint-lean repository-settings OWNER/REPO [--apply]
```

Without `--apply` it prints the `gh api` calls it would make. With `--apply` it runs them through the `gh` CLI,
which must be logged in as an administrator of the repository: the merge options, the Actions permissions
(commit-pinned actions, a read-only default token, workflows cannot approve pull requests) and the default-branch
ruleset (sent on stdin). A failing call is reported and the rest still run.

Exit codes: `0` done, `1` a call failed, `2` the repository is not `OWNER/REPO`.

## `smoke`

Lint upstream's good and bad fixtures with a built image, one linter at a time.

```text
superlint-lean smoke <image> <plan.json> <upstream-dir>
```

| Argument | Description |
| :--- | :--- |
| `image` | The image to test, for example the one built from `generate`'s output. |
| `plan.json` | Written by `generate`; its `flags` list says which linters to test. |
| `upstream-dir` | A Super-Linter checkout at the tag the image was built from (only `test/linters` and `.editorconfig` are read). |

Prints a Markdown table with one row per flag. A flag passes when the good files pass and the bad files fail
in the Super-Linter summary; a linter that found no files counts as a failure. Flags without a fixture
directory are reported, not failed.

Exit codes: `0` every flag behaved, `1` at least one did not, `2` the plan could not be read.
