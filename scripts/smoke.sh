#!/usr/bin/env bash
# Smoke-test a built image: for every selected linter, run the image on a known
# good and a known bad file and check the outcome.
#
# Usage: scripts/smoke.sh <image> <plan.json> <upstream-dir>
#
#   plan.json      written by `superlint-lean generate` (its "flags" list)
#   upstream-dir   a Super-Linter checkout at the tag the image was built from;
#                  only test/linters and .editorconfig are read (MIT licensed,
#                  not copied into this repository)
#
# Each flag uses test/linters/<flag in lower case>. Files with "good" in their
# path must pass and files with "bad" must fail, judged by the Super-Linter
# summary, so a linter that found no files to lint does not count as a pass.
# Only that one linter is enabled, so the run also shows that the image lints
# with a lean flag set. Upstream's own TEST_CASE_RUN mode is not usable: it
# refuses to run unless every validation is enabled.
set -euo pipefail

image="${1:?image}"
plan="${2:?plan.json}"
upstream="${3:?upstream dir}"
fixtures="$upstream/test/linters"

work="$(mktemp -d)"
failed=0

# The container runs as root, so its output is removed from inside an image.
# shellcheck disable=SC2329 # called by the EXIT trap
cleanup() {
  docker run --rm -v "$work:/work" --entrypoint sh "$image" -c 'rm -rf /work/* /work/.[!.]*' >/dev/null 2>&1 || true
  rm -rf "$work" 2>/dev/null || true
}
trap cleanup EXIT

# result <flag> <good|bad> <fixture dir>: pass, fail, not-linted or no-files
result() {
  local flag="$1" kind="$2" dir="$3" repo="$work/$1-$2" dest="$work/$1-$2"
  case "$flag" in
    GITHUB_ACTIONS | GITHUB_ACTIONS_ZIZMOR) dest="$repo/.github/workflows" ;; # only linted there
  esac
  mkdir -p "$dest"
  (cd "$dir" && find . -type f -ipath "*${kind}*" -exec cp --parents {} "$dest" \;)
  [ -n "$(ls -A "$dest")" ] || { echo no-files; return; }
  [ "$flag" != EDITORCONFIG ] || cp "$upstream/.editorconfig" "$repo/"
  git -C "$repo" init -q -b main
  git -C "$repo" add -A
  git -C "$repo" -c user.email=smoke@example.com -c user.name=smoke commit -qm fixtures
  docker run --rm \
    -e RUN_LOCAL=true -e DEFAULT_BRANCH=main -e VALIDATE_ALL_CODEBASE=true \
    -e MULTI_STATUS=false -e ENABLE_GITHUB_PULL_REQUEST_SUMMARY_COMMENT=false \
    -e SAVE_SUPER_LINTER_SUMMARY=true -e LOG_LEVEL=ERROR \
    -e "VALIDATE_${flag}=true" \
    -v "$repo:/tmp/lint" "$image" >"$work/$flag-$kind.log" 2>&1 || true
  local row
  row="$(grep -E "^\| ${flag} +\|" "$repo/super-linter-output/super-linter-summary.md" 2>/dev/null || true)"
  case "$row" in
    *Pass*) echo pass ;;
    *Fail*) echo fail ;;
    *) echo not-linted ;;
  esac
}

printf '| Flag | Good file | Bad file |\n| --- | --- | --- |\n'
for flag in $(jq -r '.flags[]' "$plan"); do
  dir="$fixtures/$(echo "$flag" | tr '[:upper:]' '[:lower:]')"
  if [ ! -d "$dir" ]; then
    printf '| %s | no fixture | no fixture |\n' "$flag"
    continue
  fi
  good="$(result "$flag" good "$dir")"
  bad="$(result "$flag" bad "$dir")"
  g=ok; b=ok
  case "$good" in pass) ;; no-files) g="no good file" ;; *) g="FAIL ($good)"; failed=1 ;; esac
  case "$bad" in fail) ;; no-files) b="no bad file" ;; *) b="FAIL ($bad)"; failed=1 ;; esac
  printf '| %s | %s | %s |\n' "$flag" "$g" "$b"
done

exit "$failed"
