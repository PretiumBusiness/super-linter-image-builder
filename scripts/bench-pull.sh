#!/usr/bin/env bash
# Measure cold pull time of a container image.
#
# Usage: scripts/bench-pull.sh <image> <runs> <variant> <runner-label>
#
# Appends one JSON object per run to $BENCH_OUT (default: bench-results.jsonl).
#
# Per run it removes the local image, then times `docker pull`. If `crane` is
# on PATH it also times a download-only pull to a tarball and a `docker load`
# of that tarball, to give a rough download vs unpack split (approximate: load
# is not identical to the unpack done by `docker pull`).
set -euo pipefail

image="${1:?image}"
runs="${2:-5}"
variant="${3:-$image}"
runner="${4:-unknown}"
out="${BENCH_OUT:-bench-results.jsonl}"

now() { date +%s.%N; }
elapsed() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.2f", b - a }'; }

have_crane=false
if command -v crane >/dev/null 2>&1; then have_crane=true; fi

compressed_bytes=null
if [ "$have_crane" = true ]; then
  compressed_bytes="$(crane manifest --platform linux/amd64 "$image" 2>/dev/null \
    | jq '[.layers[].size] | add' 2>/dev/null || echo null)"
fi

for i in $(seq 1 "$runs"); do
  docker image rm -f "$image" >/dev/null 2>&1 || true

  t0="$(now)"
  docker pull --quiet "$image" >/dev/null
  t1="$(now)"
  pull_s="$(elapsed "$t0" "$t1")"

  download_s=null
  load_s=null
  if [ "$have_crane" = true ]; then
    docker image rm -f "$image" >/dev/null 2>&1 || true
    tarball="$(mktemp --suffix=.tar)"
    t2="$(now)"
    crane pull --platform linux/amd64 "$image" "$tarball" >/dev/null 2>&1 || true
    t3="$(now)"
    docker load --quiet -i "$tarball" >/dev/null 2>&1 || true
    t4="$(now)"
    rm -f "$tarball"
    download_s="$(elapsed "$t2" "$t3")"
    load_s="$(elapsed "$t3" "$t4")"
  fi

  uncompressed_bytes="$(docker image inspect --format '{{.Size}}' "$image" 2>/dev/null || echo null)"
  if [ "$uncompressed_bytes" = "null" ]; then
    # image was removed for the crane split; pull again just to read the size
    docker pull --quiet "$image" >/dev/null
    uncompressed_bytes="$(docker image inspect --format '{{.Size}}' "$image")"
  fi

  jq -nc \
    --arg image "$image" --arg variant "$variant" --arg runner "$runner" \
    --argjson run "$i" --argjson pull_s "$pull_s" \
    --argjson download_s "$download_s" --argjson load_s "$load_s" \
    --argjson compressed_bytes "${compressed_bytes:-null}" \
    --argjson uncompressed_bytes "$uncompressed_bytes" \
    '{image:$image, variant:$variant, runner:$runner, run:$run,
      pull_s:$pull_s, download_s:$download_s, load_s:$load_s,
      compressed_bytes:$compressed_bytes, uncompressed_bytes:$uncompressed_bytes}' \
    | tee -a "$out"
done
