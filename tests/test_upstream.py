"""Tests for superlint_lean.upstream."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from superlint_lean import cli, upstream

TEST_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
TEST_PINNED = "v9.0.0"
TEST_NEWER = "v9.1.0"
TEST_NEWEST = "v9.2.0"


def release(tag: str, published_at: str, draft: bool = False, prerelease: bool = False) -> dict[str, Any]:
    return {"tag_name": tag, "published_at": published_at, "draft": draft, "prerelease": prerelease}


TEST_RELEASES = [
    release(TEST_NEWEST, "2026-10-12T12:00:00Z"),
    release(TEST_NEWER, "2026-10-01T12:00:00Z"),
    release(TEST_PINNED, "2026-09-01T12:00:00Z"),
]


@pytest.fixture
def pinned_file(tmp_path: Path) -> Path:
    path = tmp_path / "upstream-version.txt"
    path.write_text(f"{TEST_PINNED}\n")
    return path


@pytest.fixture
def github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(path))
    return path


class TestVersionKey:
    def test_version_key_should_order_a_higher_minor_after_a_lower_one_when_both_have_two_digits(self) -> None:
        older = upstream.version_key("v9.9.0")
        newer = upstream.version_key("v9.10.0")

        assert older < newer


class TestEligible:
    def test_eligible_should_return_the_newest_release_when_the_cooldown_is_zero(self) -> None:
        tag = upstream.eligible(TEST_RELEASES, 0, TEST_NOW)

        assert tag == TEST_NEWEST

    def test_eligible_should_skip_releases_younger_than_the_cooldown_when_one_is_old_enough(self) -> None:
        tag = upstream.eligible(TEST_RELEASES, 7, TEST_NOW)

        assert tag == TEST_NEWER

    def test_eligible_should_return_an_empty_string_when_every_release_is_younger_than_the_cooldown(self) -> None:
        tag = upstream.eligible(TEST_RELEASES, 365, TEST_NOW)

        assert tag == ""

    def test_eligible_should_skip_drafts_and_prereleases_when_they_are_the_newest(self) -> None:
        releases = [
            release("v9.3.0", "2026-10-12T12:00:00Z", draft=True),
            release("v9.3.0-rc1", "2026-10-11T12:00:00Z", prerelease=True),
            *TEST_RELEASES,
        ]

        tag = upstream.eligible(releases, 0, TEST_NOW)

        assert tag == TEST_NEWEST


class TestIsBehind:
    def test_is_behind_should_return_true_when_the_latest_is_newer(self) -> None:
        behind = upstream.is_behind(TEST_PINNED, TEST_NEWER)

        assert behind

    def test_is_behind_should_return_false_when_the_latest_equals_the_pinned_tag(self) -> None:
        behind = upstream.is_behind(TEST_PINNED, TEST_PINNED)

        assert not behind

    def test_is_behind_should_return_false_when_the_latest_is_older_than_the_pinned_tag(self) -> None:
        behind = upstream.is_behind(TEST_NEWER, TEST_PINNED)

        assert not behind


class TestMain:
    def test_main_should_write_behind_true_and_the_latest_tag_when_upstream_is_ahead(
        self,
        pinned_file: Path,
        github_output: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(upstream, "fetch_releases", lambda repo: TEST_RELEASES)

        code = upstream.main(["--pinned-file", str(pinned_file)])

        written = github_output.read_text()
        printed = capsys.readouterr().out
        assert code == 0
        assert written == f"pinned={TEST_PINNED}\nlatest={TEST_NEWEST}\nbehind=true\n"
        assert "behind upstream" in printed

    def test_main_should_write_behind_false_when_the_pinned_tag_is_the_newest(
        self,
        pinned_file: Path,
        github_output: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(upstream, "fetch_releases", lambda repo: TEST_RELEASES[-1:])

        code = upstream.main(["--pinned-file", str(pinned_file)])

        written = github_output.read_text()
        printed = capsys.readouterr().out
        assert code == 0
        assert "behind=false" in written
        assert "Nothing to do" in printed

    def test_main_should_keep_the_pinned_tag_and_report_none_when_no_release_is_old_enough(
        self,
        pinned_file: Path,
        github_output: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(upstream, "fetch_releases", lambda repo: TEST_RELEASES[:2])

        code = upstream.main(["--pinned-file", str(pinned_file), "--cooldown-days", "36500"])

        written = github_output.read_text()
        printed = capsys.readouterr().out
        assert code == 0
        assert f"latest={TEST_PINNED}\n" in written
        assert "newest eligible upstream release is 'none'" in printed

    def test_main_should_use_the_forced_tag_without_reading_the_releases_when_force_tag_is_given(
        self, pinned_file: Path, github_output: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail(repo: str) -> list[dict[str, Any]]:
            raise AssertionError("the releases must not be read")

        monkeypatch.setattr(upstream, "fetch_releases", fail)

        code = upstream.main(["--pinned-file", str(pinned_file), "--force-tag", TEST_NEWER])

        assert code == 0
        assert f"latest={TEST_NEWER}\nbehind=true\n" in github_output.read_text()

    def test_main_should_return_two_when_the_cooldown_is_not_a_whole_number(
        self, pinned_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = upstream.main(["--pinned-file", str(pinned_file), "--cooldown-days", "soon"])

        assert code == 2
        assert "cooldown_days must be a whole number, got 'soon'" in capsys.readouterr().out

    def test_main_should_return_two_when_the_pinned_file_is_missing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = upstream.main(["--pinned-file", str(tmp_path / "missing.txt")])

        assert code == 2
        assert "cannot read" in capsys.readouterr().out

    def test_main_should_return_two_when_the_releases_cannot_be_read(
        self, pinned_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def broken(repo: str) -> list[dict[str, Any]]:
            raise subprocess.CalledProcessError(1, "gh")

        monkeypatch.setattr(upstream, "fetch_releases", broken)

        code = upstream.main(["--pinned-file", str(pinned_file)])

        assert code == 2
        assert "cannot read the releases" in capsys.readouterr().out

    def test_main_should_print_only_when_github_output_is_not_set(
        self, pinned_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        monkeypatch.setattr(upstream, "fetch_releases", lambda repo: TEST_RELEASES)

        code = upstream.main(["--pinned-file", str(pinned_file)])

        assert code == 0


class TestFetchReleases:
    def test_fetch_releases_should_parse_the_gh_output_when_the_call_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> Any:
            seen.append(command)
            return subprocess.CompletedProcess(command, 0, stdout='[{"tag_name": "v9.0.0"}]')

        monkeypatch.setattr(subprocess, "run", fake_run)

        releases = upstream.fetch_releases("owner/repo")

        assert releases == [{"tag_name": "v9.0.0"}]
        assert seen[0][:2] == ["gh", "api"]
        assert "repos/owner/repo/releases" in seen[0][2]


class TestCli:
    def test_cli_main_should_list_select_upstream_when_help_is_requested(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main(["--help"])

        assert code == 0
        assert "select-upstream" in capsys.readouterr().out
