#!/usr/bin/env bash
# Profile an image's layers for sim/pull_model.py --measured.
#
# Usage: sim/profile-image.sh <image> <out.json>
#
# Writes [{"comp_mb", "unc_mb", "files"}, ...] in layer order. Needs docker,
# crane, jq and tar. Run it on any machine with registry access (for example
# the pretium runner). Requires the classic `docker save` format (manifest.json).
set -euo pipefail

image="${1:?image}"
out="${2:?output file}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

docker pull --quiet "$image" >/dev/null
docker save "$image" | tar -x -C "$tmp"

if [ ! -f "$tmp/manifest.json" ]; then
  echo "docker save did not produce manifest.json (containerd image store?)." >&2
  echo "Disable the containerd image store or export with 'crane export' per layer." >&2
  exit 1
fi

comp_sizes="$(crane manifest --platform linux/amd64 "$image" | jq -c '[.layers[].size]')"

i=0
layers='[]'
while IFS= read -r layer; do
  unc="$(stat -c %s "$tmp/$layer")"
  files="$(tar -tf "$tmp/$layer" | wc -l)"
  comp="$(jq -r ".[$i]" <<<"$comp_sizes")"
  layers="$(jq -c --argjson c "$comp" --argjson u "$unc" --argjson f "$files" \
    '. + [{comp_mb: ($c / 1048576), unc_mb: ($u / 1048576), files: $f}]' <<<"$layers")"
  i=$((i + 1))
done < <(jq -r '.[0].Layers[]' "$tmp/manifest.json")

jq . <<<"$layers" > "$out"
echo "wrote $out ($i layers)"
