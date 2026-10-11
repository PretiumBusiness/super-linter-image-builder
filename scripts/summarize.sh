#!/usr/bin/env bash
# Turn bench-results.jsonl files into a Markdown table (median of runs).
#
# Usage: scripts/summarize.sh <file.jsonl>...
set -euo pipefail

jq -s -r '
  def median: sort | if length == 0 then null
              elif length % 2 == 1 then .[(length - 1) / 2]
              else (.[length / 2 - 1] + .[length / 2]) / 2 end;
  def mb: if . == null then "n/a" else (. / 1048576 | floor | tostring) + " MB" end;
  def s:  if . == null then "n/a" else (. * 10 | round / 10 | tostring) + " s" end;

  "| Runner | Variant | Runs | Pull median | Pull min-max | Download (crane) | Load | Compressed | Uncompressed |",
  "|---|---|---|---|---|---|---|---|---|",
  (flatten | group_by([.runner, .variant])[] |
    . as $g | $g[0] as $f |
    "| \($f.runner) | \($f.variant) | \($g | length) | \([$g[].pull_s] | median | s) | \([$g[].pull_s] | min | s)-\([$g[].pull_s] | max | s) | \([$g[] | select(.download_s != null) | .download_s] | median | s) | \([$g[] | select(.load_s != null) | .load_s] | median | s) | \($f.compressed_bytes | mb) | \($f.uncompressed_bytes | mb) |")
' "$@"
