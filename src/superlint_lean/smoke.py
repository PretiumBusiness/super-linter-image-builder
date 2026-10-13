"""Smoke-test a built image against Super-Linter's own good and bad fixtures.

Usage:
    superlint-lean smoke <image> <plan.json> <upstream-dir>

    plan.json     written by ``superlint-lean generate`` (its "flags" list)
    upstream-dir  a Super-Linter checkout at the tag the image was built from;
                  only ``test/linters`` and ``.editorconfig`` are read (MIT
                  licensed, never copied into this repository or the image)

Each flag uses ``test/linters/<flag in lower case>``. Files with "good" in their
path must pass and files with "bad" must fail, judged by the Super-Linter
summary, so a linter that found no files to lint does not count as a pass.
Only that one linter is enabled, so the run also shows that the image lints
with a lean flag set. Upstream's own ``TEST_CASE_RUN`` mode cannot be used: it
refuses to run unless every validation is enabled.

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


def docker_command(image: str, repo: Path, flag: str) -> list[str]:
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
        "-e",
        f"VALIDATE_{flag}=true",
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


def run_image(image: str, repo: Path, flag: str) -> None:
    """Run the image on `repo`. A failing lint exits non-zero; the verdict comes from the summary."""
    subprocess.run(docker_command(image, repo, flag), check=False, capture_output=True)


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
    run_image(image, repo, flag)
    summary = repo / SUMMARY
    return verdict(summary.read_text() if summary.exists() else "", flag)


def cell(outcome: str, expected: str, label: str) -> tuple[str, bool]:
    """Table cell and whether it is a failure."""
    if outcome == expected:
        return "ok", False
    if outcome == NO_FILES:
        return f"no {label} file", False
    return f"FAIL ({outcome})", True


def smoke(image: str, flags: Sequence[str], upstream: Path) -> tuple[list[str], bool]:
    """The Markdown table lines and whether every flag behaved."""
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
    finally:
        clear_directory(image, work)
    return lines, ok


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="the image to test")
    ap.add_argument("plan", help="plan.json written by `superlint-lean generate`")
    ap.add_argument("upstream", help="a Super-Linter checkout at the tag the image was built from")
    args = ap.parse_args(argv)

    try:
        flags: list[str] = json.loads(Path(args.plan).read_text())["flags"]
    except (OSError, ValueError, KeyError) as e:
        print(f"::error::cannot read the flags from {args.plan}: {e}")
        return 2
    lines, ok = smoke(args.image, flags, Path(args.upstream))
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
