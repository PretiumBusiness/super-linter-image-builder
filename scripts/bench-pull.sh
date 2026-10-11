#!/usr/bin/env bash
# Measure pull time and container start time of an image.
#
# Usage: scripts/bench-pull.sh <image> <runs> <variant> <runner-label>
#
# Environment:
#   BENCH_MODE  cold (default) or warm
#     cold  remove the local image before every run, then time `docker pull`
#     warm  image stays on the runner (a self-hosted runner with the image
#           preloaded); time the no-op `docker pull`, which is what a job pays
#           when nothing needs downloading
#   BENCH_OUT   JSON lines output file (default: bench-results.jsonl)
#   BENCH_SPLIT 1 to also measure a download-only pull and a `docker load` in
#               cold mode (needs crane; roughly triples the time per run)
#
# Appends one JSON object per run to $BENCH_OUT.
#
# With BENCH_SPLIT=1 in cold mode it also times a download-only pull to a
# tarball and a `docker load` of that tarball, to give a rough download vs
# unpack split (approximate: load is not identical to the unpack done by
# `docker pull`). Without it, crane (if present) is only used to read the
# compressed image size.
set -euo pipefail

image="${1:?image}"
runs="${2:-5}"
variant="${3:-$image}"
runner="${4:-unknown}"
mode="${BENCH_MODE:-cold}"
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

if [ "$mode" = "warm" ]; then
  # Make sure the image is present; this first pull is not measured.
  docker pull --quiet "$image" >/dev/null
fi

for i in $(seq 1 "$runs"); do
  download_s=null
  load_s=null

  if [ "$mode" = "cold" ]; then
    docker image rm -f "$image" >/dev/null 2>&1 || true
  fi

  t0="$(now)"
  docker pull --quiet "$image" >/dev/null
  t1="$(now)"
  pull_s="$(elapsed "$t0" "$t1")"

  # Time to start a container from the image (layers are already unpacked).
  t5="$(now)"
  docker run --rm --entrypoint true "$image" >/dev/null 2>&1 || true
  t6="$(now)"
  start_s="$(elapsed "$t5" "$t6")"

  uncompressed_bytes="$(docker image inspect --format '{{.Size}}' "$image")"

  if [ "$mode" = "cold" ] && [ "$have_crane" = true ] && [ "${BENCH_SPLIT:-0}" = "1" ]; then
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

  jq -nc \
    --arg image "$image" --arg variant "$variant" --arg runner "$runner" --arg mode "$mode" \
    --argjson run "$i" --argjson pull_s "$pull_s" --argjson start_s "$start_s" \
    --argjson download_s "$download_s" --argjson load_s "$load_s" \
    --argjson compressed_bytes "${compressed_bytes:-null}" \
    --argjson uncompressed_bytes "$uncompressed_bytes" \
    '{image:$image, variant:$variant, runner:$runner, mode:$mode, run:$run,
      pull_s:$pull_s, start_s:$start_s, download_s:$download_s, load_s:$load_s,
      compressed_bytes:$compressed_bytes, uncompressed_bytes:$uncompressed_bytes}' \
    | tee -a "$out"
done
