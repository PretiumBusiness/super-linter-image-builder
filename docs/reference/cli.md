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
