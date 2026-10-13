"""Smoke-test a built image against Super-Linter's own good and bad fixtures.

Usage:
    superlint-lean smoke <image> <plan.json> <upstream-dir> [--mapping linters.json]

    plan.json
        written by ``superlint-lean generate`` (its "flags" list)
    upstream-dir
        a Super-Linter checkout at the tag the image was built from; only
        ``test/linters`` and ``.editorconfig`` are read (MIT licensed, never
        copied into this repository or the image)

Each flag uses ``test/linters/<flag in lower case>``. Files with "good" in their
path must pass and files with "bad" must fail, judged by the Super-Linter
summary, so a linter that found no files to lint does not count as a pass.
Only that one linter is enabled, so the run also shows that the image lints
with a lean flag set. Upstream's own ``TEST_CASE_RUN`` mode cannot be used: it
refuses to run unless every validation is enabled.

Then it enables every flag of the plan at once, puts the bad fixtures of the
mapped linters that are not enabled into the repository, and checks that none
of them shows up in the summary: a disabled linter is skipped, not run and not
failing.

Prints a Markdown table. Exit code: 0 every flag behaved, 1 at least one did
not, 2 a bad argument.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

MAPPING = Path(__file__).resolve().parent / "data" / "linters.json"

# these linters only look at files under .github/workflows
WORKFLOW_FLAGS = frozenset({"GITHUB_ACTIONS", "GITHUB_ACTIONS_ZIZMOR"})
SUMMARY = Path("super-linter-output") / "super-linter-summary.md"

CLEAN = "pass"
ERRORS = "fail"
NOT_LINTED = "not-linted"
NO_FILES = "no-files"


def fixture_dir(upstream: Path, flag: str) -> Path:
    return upstream / "test" / "linters" / flag.lower()


def destination(repo: Path, flag: str) -> Path:
    return repo / ".github" / "workflows" if flag in WORKFLOW_FLAGS else repo


def copy_fixtures(source: Path, kind: str, dest: Path) -> int:
    """Copy the files of `source` with `kind` ("good" or "bad") in their path; return how many."""
    copied = 0
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        relative = path.relative_to(source)
        if kind not in relative.as_posix().lower():
            continue
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def verdict(summary: str, flag: str) -> str:
    """What the Super-Linter summary says about `flag`: pass, fail or not-linted."""
    for line in summary.splitlines():
        match = re.match(rf"^\|\s*{re.escape(flag)}\s*\|(.*)\|", line)
        if match:
            if "Pass" in match.group(1):
                return CLEAN
            if "Fail" in match.group(1):
                return ERRORS
    return NOT_LINTED


def docker_command(image: str, repo: Path, flags: Sequence[str]) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "-e",
        "RUN_LOCAL=true",
        "-e",
        "DEFAULT_BRANCH=main",
        "-e",
        "VALIDATE_ALL_CODEBASE=true",
        "-e",
        "MULTI_STATUS=false",
        "-e",
        "ENABLE_GITHUB_PULL_REQUEST_SUMMARY_COMMENT=false",
        "-e",
        "SAVE_SUPER_LINTER_SUMMARY=true",
        "-e",
        "LOG_LEVEL=ERROR",
        *[arg for flag in flags for arg in ("-e", f"VALIDATE_{flag}=true")],
        "-v",
        f"{repo}:/tmp/lint",
        image,
    ]


def init_repository(repo: Path) -> None:
    """Super-Linter lints a git repository; commit the copied fixtures."""
    for args in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        ["-c", "user.email=smoke@example.com", "-c", "user.name=smoke", "commit", "-qm", "fixtures"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def run_image(image: str, repo: Path, flags: Sequence[str]) -> None:
    """Run the image on `repo`. A failing lint exits non-zero; the verdict comes from the summary."""
    subprocess.run(docker_command(image, repo, flags), check=False, capture_output=True)


def clear_directory(image: str, work: Path) -> None:
    """The container runs as root, so remove its output from inside an image."""
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{work}:/work",
            "--entrypoint",
            "sh",
            image,
            "-c",
            "rm -rf /work/* /work/.[!.]*",
        ],
        check=False,
        capture_output=True,
    )
    shutil.rmtree(work, ignore_errors=True)


def result(image: str, flag: str, kind: str, source: Path, upstream: Path, work: Path) -> str:
    """pass, fail, not-linted, or no-files when the fixtures have no `kind` file."""
    repo = work / f"{flag}-{kind}"
    if copy_fixtures(source, kind, destination(repo, flag)) == 0:
        return NO_FILES
    if flag == "EDITORCONFIG":
        shutil.copy2(upstream / ".editorconfig", repo / ".editorconfig")
    init_repository(repo)
    run_image(image, repo, [flag])
    summary = repo / SUMMARY
    return verdict(summary.read_text() if summary.exists() else "", flag)


def skipped(image: str, enabled: Sequence[str], mapped: Sequence[str], upstream: Path, work: Path) -> tuple[str, bool]:
    """Run every enabled linter on the bad files of the disabled ones; the disabled must not appear."""
    disabled = [flag for flag in mapped if flag not in enabled and fixture_dir(upstream, flag).is_dir()]
    if not disabled:
        return "Disabled linters: none to test", True
    repo = work / "disabled"
    for flag in disabled:
        copy_fixtures(fixture_dir(upstream, flag), "bad", destination(repo, flag))
    probe = next((flag for flag in enabled if fixture_dir(upstream, flag).is_dir()), "")
    if probe:
        copy_fixtures(fixture_dir(upstream, probe), "good", destination(repo, probe))
    init_repository(repo)
    run_image(image, repo, enabled)
    summary = repo / SUMMARY
    text = summary.read_text() if summary.exists() else ""
    if probe and verdict(text, probe) == NOT_LINTED:
        return f"Disabled linters: FAIL (the image did not lint: {probe} is missing from the summary)", False
    ran = [flag for flag in disabled if verdict(text, flag) != NOT_LINTED]
    if ran:
        return f"Disabled linters: FAIL (ran although disabled: {', '.join(ran)})", False
    return f"Disabled linters: ok ({len(disabled)} skipped)", True


def cell(outcome: str, expected: str, label: str) -> tuple[str, bool]:
    """Table cell and whether it is a failure."""
    if outcome == expected:
        return "ok", False
    if outcome == NO_FILES:
        return f"no {label} file", False
    return f"FAIL ({outcome})", True


def smoke(image: str, flags: Sequence[str], upstream: Path, mapped: Sequence[str] = ()) -> tuple[list[str], bool]:
    """The Markdown lines and whether every flag behaved and the disabled linters were skipped."""
    lines = ["| Flag | Good file | Bad file |", "| --- | --- | --- |"]
    ok = True
    work = Path(tempfile.mkdtemp())
    try:
        for flag in flags:
            source = fixture_dir(upstream, flag)
            if not source.is_dir():
                lines.append(f"| {flag} | no fixture | no fixture |")
                continue
            good, good_failed = cell(result(image, flag, "good", source, upstream, work), CLEAN, "good")
            bad, bad_failed = cell(result(image, flag, "bad", source, upstream, work), ERRORS, "bad")
            ok = ok and not good_failed and not bad_failed
            lines.append(f"| {flag} | {good} | {bad} |")
        line, skipped_ok = skipped(image, flags, mapped, upstream, work)
        ok = ok and skipped_ok
        lines += ["", line]
    finally:
        clear_directory(image, work)
    return lines, ok


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="the image to test")
    ap.add_argument("plan", help="plan.json written by `superlint-lean generate`")
    ap.add_argument("upstream", help="a Super-Linter checkout at the tag the image was built from")
    ap.add_argument(
        "--mapping", default=str(MAPPING), help="linters.json; its flags that are not in the plan must be skipped"
    )
    args = ap.parse_args(argv)

    try:
        flags: list[str] = json.loads(Path(args.plan).read_text())["flags"]
        mapped: list[str] = list(json.loads(Path(args.mapping).read_text())["linters"])
    except (OSError, ValueError, KeyError) as e:
        print(f"::error::cannot read the flags from {args.plan} or {args.mapping}: {e}")
        return 2
    lines, ok = smoke(args.image, flags, Path(args.upstream), mapped)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
