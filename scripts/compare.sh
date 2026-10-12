#!/usr/bin/env bash
# Compare lean images against their upstream baseline, per profile.
#
# Usage: scripts/compare.sh bench-*.jsonl
#
# Input rows carry variant "<profile>/<kind>" with kind baseline, lean-gzip or
# lean-zstd, and mode cold or warm (see scripts/bench-pull.sh).
set -euo pipefail

jq -s -r '
  def median: sort | if length == 0 then null
              elif length % 2 == 1 then .[(length - 1) / 2]
              else (.[length / 2 - 1] + .[length / 2]) / 2 end;
  def s:  if . == null then "n/a" else (. * 10 | round / 10 | tostring) + " s" end;
  def mb: if . == null then null else (. / 1048576 | round) end;
  def mbs: if . == null then "n/a" else (. | tostring) + " MB" end;
  def pct($a; $b): if $a == null or $b == null or $a == 0 then "n/a"
                  else ((1 - $b / $a) * 100 | round | tostring) + "%" end;
  def drift($a; $b): if $a == null or $b == null or $a == 0 then "n/a"
                    else (($b - $a) / $a * 100) as $d
                          | (if ($d | fabs) > 15 then "WARN " else "" end) + ($d | round | tostring) + "%" end;
  def x($a; $b): if $a == null or $b == null or $b == 0 then "n/a"
                else (($a / $b) * 10 | round / 10 | tostring) + "x" end;

  flatten
  | map(. + {profile: (.variant | split("/")[0]), kind: (.variant | split("/")[1]),
            mode: (.mode // "cold")})
  | group_by(.profile) as $profiles
  | ( "### Cold pull (image removed before each pull)",
      "",
      "| Profile | Baseline | Lean gzip | Lean zstd | Speedup (gzip) | Speedup (zstd) | Baseline unpacked | Lean unpacked | Unpacked saved | Baseline compressed | Lean compressed | Compressed saved | Baseline drift | Build gzip | Build zstd |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
      ( $profiles[] | . as $rows | $rows[0].profile as $p
        | def sel($k; $m): $rows | map(select(.kind == $k and .mode == $m));
          def med($k; $m): [sel($k; $m)[].pull_s] | median;
          def sz($k; $f): (sel($k; "cold")[0] // {}) | .[$f] | mb;
        "| \($p) | \(med("baseline"; "cold") | s) | \(med("lean-gzip"; "cold") | s) | \(med("lean-zstd"; "cold") | s) | \(x(med("baseline"; "cold"); med("lean-gzip"; "cold"))) | \(x(med("baseline"; "cold"); med("lean-zstd"; "cold"))) | \(sz("baseline"; "uncompressed_bytes") | mbs) | \(sz("lean-gzip"; "uncompressed_bytes") | mbs) | \(pct(sz("baseline"; "uncompressed_bytes"); sz("lean-gzip"; "uncompressed_bytes"))) | \(sz("baseline"; "compressed_bytes") | mbs) | \(sz("lean-gzip"; "compressed_bytes") | mbs) | \(pct(sz("baseline"; "compressed_bytes"); sz("lean-gzip"; "compressed_bytes"))) | \(drift(med("baseline"; "cold"); med("baseline-end"; "cold"))) | \(med("lean-gzip"; "build") | s) | \(med("lean-zstd"; "build") | s) |" ),
      "",
      "### Warm pull (image already on the runner) and container start",
      "",
      "| Profile | Baseline pull | Lean gzip pull | Baseline start | Lean gzip start |",
      "|---|---|---|---|---|",
      ( $profiles[] | . as $rows | $rows[0].profile as $p
        | def sel($k): $rows | map(select(.kind == $k and .mode == "warm"));
          def pull($k): [sel($k)[].pull_s] | median;
          def start($k): [sel($k)[] | select(.start_s != null) | .start_s] | median;
        "| \($p) | \(pull("baseline") | s) | \(pull("lean-gzip") | s) | \(start("baseline") | s) | \(start("lean-gzip") | s) |" )
    )
' "$@"
