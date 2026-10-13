"""Tests for superlint_lean.smoke."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from superlint_lean import smoke

TEST_IMAGE = "img:1"
TEST_FLAG = "YAML"
TEST_GOOD_FILE = "yml_good_1.yml"
TEST_BAD_FILE = "yml_bad_1.yml"
TEST_EDITORCONFIG = "root = true\n"
TEST_SUMMARY_HEADER = "| Language | Validation result |\n| --- | --- |\n"
TEST_SUMMARY_PASS = TEST_SUMMARY_HEADER + "| YAML     | Pass ✅           |\n"
TEST_SUMMARY_FAIL = TEST_SUMMARY_HEADER + "| YAML     | Fail ❌           |\n"
TEST_DISABLED_FLAG = "JSON"
TEST_SUMMARY_DISABLED_RAN = TEST_SUMMARY_PASS + "| JSON     | Fail ❌           |\n"


def write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def make_upstream(root: Path, flag: str, file_names: list[str]) -> Path:
    fixtures = root / "test" / "linters" / flag.lower()
    for file_name in file_names:
        write(fixtures / file_name)
    write(root / ".editorconfig", TEST_EDITORCONFIG)
    return root


def make_plan(path: Path, flags: list[str]) -> Path:
    path.write_text(json.dumps({"flags": flags}))
    return path


@pytest.fixture
def fake_docker(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Path]]:
    """Replace git and docker: the fake image writes a Fail summary when the repository holds a bad file."""
    calls: list[tuple[str, Path]] = []

    def fake_run_image(image: str, repo: Path, flags: list[str]) -> None:
        flag = flags[0]
        calls.append((flag, repo))
        has_bad_file = any("bad" in found.name for found in repo.rglob("*") if found.is_file())
        summary = TEST_SUMMARY_FAIL if has_bad_file else TEST_SUMMARY_PASS
        write(repo / smoke.SUMMARY, summary.replace(TEST_FLAG + "    ", f"{flag:<8}"))

    monkeypatch.setattr(smoke, "init_repository", lambda repo: None)
    monkeypatch.setattr(smoke, "run_image", fake_run_image)
    monkeypatch.setattr(smoke, "clear_directory", lambda image, work: None)
    return calls


class TestVerdict:
    def test_verdict_should_return_clean_when_the_summary_row_says_pass(self) -> None:
        outcome = smoke.verdict(TEST_SUMMARY_PASS, TEST_FLAG)

        assert outcome == smoke.CLEAN

    def test_verdict_should_return_errors_when_the_summary_row_says_fail(self) -> None:
        outcome = smoke.verdict(TEST_SUMMARY_FAIL, TEST_FLAG)

        assert outcome == smoke.ERRORS

    def test_verdict_should_return_not_linted_when_the_flag_is_not_in_the_summary(self) -> None:
        outcome = smoke.verdict(TEST_SUMMARY_PASS, "JSON")

        assert outcome == smoke.NOT_LINTED

    def test_verdict_should_not_match_a_longer_flag_when_it_shares_the_prefix(self) -> None:
        summary = "| GITHUB_ACTIONS_ZIZMOR | Pass ✅ |\n"

        outcome = smoke.verdict(summary, "GITHUB_ACTIONS")

        assert outcome == smoke.NOT_LINTED


class TestCopyFixtures:
    def test_copy_fixtures_should_copy_only_files_with_the_kind_in_their_path_when_both_kinds_exist(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "src"
        write(source / "a_good_1.yml")
        write(source / "a_bad_1.yml")
        write(source / "bad" / "nested.txt")
        destination = tmp_path / "dest"

        copied = smoke.copy_fixtures(source, "bad", destination)

        copied_names = sorted(found.name for found in destination.rglob("*") if found.is_file())
        assert copied == 2
        assert copied_names == ["a_bad_1.yml", "nested.txt"]

    def test_copy_fixtures_should_return_zero_when_no_file_matches(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        write(source / "a_good_1.yml")

        copied = smoke.copy_fixtures(source, "bad", tmp_path / "dest")

        assert copied == 0


class TestDestination:
    def test_destination_should_use_the_workflows_directory_when_the_flag_is_github_actions(
        self, tmp_path: Path
    ) -> None:
        destination = smoke.destination(tmp_path, "GITHUB_ACTIONS")

        assert destination == tmp_path / ".github" / "workflows"

    def test_destination_should_use_the_workflows_directory_when_the_flag_is_zizmor(self, tmp_path: Path) -> None:
        destination = smoke.destination(tmp_path, "GITHUB_ACTIONS_ZIZMOR")

        assert destination == tmp_path / ".github" / "workflows"

    def test_destination_should_use_the_repository_root_when_the_flag_lints_any_file(self, tmp_path: Path) -> None:
        destination = smoke.destination(tmp_path, TEST_FLAG)

        assert destination == tmp_path


class TestDockerCommand:
    def test_docker_command_should_enable_only_the_given_flag_when_the_command_is_built(self, tmp_path: Path) -> None:
        command = smoke.docker_command(TEST_IMAGE, tmp_path, [TEST_FLAG])

        enabled_flags = [part for part in command if part.startswith("VALIDATE_") and "ALL_CODEBASE" not in part]
        assert enabled_flags == ["VALIDATE_YAML=true"]

    def test_docker_command_should_mount_the_repository_and_end_with_the_image_when_the_command_is_built(
        self, tmp_path: Path
    ) -> None:
        command = smoke.docker_command(TEST_IMAGE, tmp_path, [TEST_FLAG])

        assert f"{tmp_path}:/tmp/lint" in command
        assert command[-1] == TEST_IMAGE


class TestDockerCommandWithSeveralFlags:
    def test_docker_command_should_enable_every_given_flag_when_several_flags_are_given(self, tmp_path: Path) -> None:
        command = smoke.docker_command(TEST_IMAGE, tmp_path, [TEST_FLAG, TEST_DISABLED_FLAG])

        enabled_flags = [part for part in command if part.startswith("VALIDATE_") and "ALL_CODEBASE" not in part]
        assert enabled_flags == ["VALIDATE_YAML=true", "VALIDATE_JSON=true"]


class TestSkipped:
    @staticmethod
    def make_fixtures(root: Path) -> Path:
        make_upstream(root, TEST_FLAG, [TEST_GOOD_FILE, TEST_BAD_FILE])
        make_upstream(root, TEST_DISABLED_FLAG, ["json_bad_1.json"])
        return root

    def test_skipped_should_pass_when_the_disabled_linter_is_absent_from_the_summary(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        upstream = self.make_fixtures(tmp_path / "up")
        monkeypatch.setattr(
            smoke, "run_image", lambda image, repo, flags: write(repo / smoke.SUMMARY, TEST_SUMMARY_PASS)
        )

        line, ok = smoke.skipped(TEST_IMAGE, [TEST_FLAG], [TEST_FLAG, TEST_DISABLED_FLAG], upstream, tmp_path / "work")

        assert ok
        assert line == "Disabled linters: ok (1 skipped)"

    def test_skipped_should_fail_and_name_the_linter_when_a_disabled_linter_appears_in_the_summary(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        upstream = self.make_fixtures(tmp_path / "up")
        monkeypatch.setattr(
            smoke, "run_image", lambda image, repo, flags: write(repo / smoke.SUMMARY, TEST_SUMMARY_DISABLED_RAN)
        )

        line, ok = smoke.skipped(TEST_IMAGE, [TEST_FLAG], [TEST_FLAG, TEST_DISABLED_FLAG], upstream, tmp_path / "work")

        assert not ok
        assert "ran although disabled: JSON" in line

    def test_skipped_should_fail_when_the_image_did_not_lint_anything(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        upstream = self.make_fixtures(tmp_path / "up")
        monkeypatch.setattr(smoke, "run_image", lambda image, repo, flags: None)

        line, ok = smoke.skipped(TEST_IMAGE, [TEST_FLAG], [TEST_FLAG, TEST_DISABLED_FLAG], upstream, tmp_path / "work")

        assert not ok
        assert "the image did not lint" in line

    def test_skipped_should_report_nothing_to_test_when_every_mapped_linter_is_enabled(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]]
    ) -> None:
        upstream = self.make_fixtures(tmp_path / "up")

        line, ok = smoke.skipped(TEST_IMAGE, [TEST_FLAG], [TEST_FLAG], upstream, tmp_path / "work")

        assert ok
        assert line == "Disabled linters: none to test"
        assert fake_docker == []

    def test_skipped_should_put_the_bad_files_of_the_disabled_linter_in_the_repository_when_it_runs(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        upstream = self.make_fixtures(tmp_path / "up")
        seen: list[bool] = []

        def fake_run_image(image: str, repo: Path, flags: list[str]) -> None:
            seen.append((repo / "json_bad_1.json").is_file())
            write(repo / smoke.SUMMARY, TEST_SUMMARY_PASS)

        monkeypatch.setattr(smoke, "run_image", fake_run_image)

        smoke.skipped(TEST_IMAGE, [TEST_FLAG], [TEST_FLAG, TEST_DISABLED_FLAG], upstream, tmp_path / "work")

        assert seen == [True]


class TestMain:
    def test_main_should_return_zero_and_print_ok_when_good_passes_and_bad_fails(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", TEST_FLAG, [TEST_GOOD_FILE, TEST_BAD_FILE])
        plan = make_plan(tmp_path / "plan.json", [TEST_FLAG])

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 0
        assert "| YAML | ok | ok |" in capsys.readouterr().out
        assert [flag for flag, _repo in fake_docker] == [TEST_FLAG, TEST_FLAG]

    def test_main_should_return_one_when_a_disabled_linter_runs(
        self,
        tmp_path: Path,
        fake_docker: list[tuple[str, Path]],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        upstream = TestSkipped.make_fixtures(tmp_path / "up")
        plan = make_plan(tmp_path / "plan.json", [TEST_FLAG])
        mapping = tmp_path / "linters.json"
        mapping.write_text(json.dumps({"linters": {TEST_FLAG: {}, TEST_DISABLED_FLAG: {}}}))
        original = smoke.run_image

        def fake_run_image(image: str, repo: Path, flags: list[str]) -> None:
            summary = TEST_SUMMARY_DISABLED_RAN if len(flags) == 1 and "disabled" in repo.name else None
            if summary is None:
                original(image, repo, flags)
            else:
                write(repo / smoke.SUMMARY, summary)

        monkeypatch.setattr(smoke, "run_image", fake_run_image)

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream), "--mapping", str(mapping)])

        assert code == 1
        assert "ran although disabled: JSON" in capsys.readouterr().out

    def test_main_should_return_one_when_the_bad_files_pass(
        self,
        tmp_path: Path,
        fake_docker: list[tuple[str, Path]],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        upstream = make_upstream(tmp_path / "up", TEST_FLAG, [TEST_GOOD_FILE, TEST_BAD_FILE])
        plan = make_plan(tmp_path / "plan.json", [TEST_FLAG])
        monkeypatch.setattr(
            smoke, "run_image", lambda image, repo, flags: write(repo / smoke.SUMMARY, TEST_SUMMARY_PASS)
        )

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 1
        assert "FAIL (pass)" in capsys.readouterr().out

    def test_main_should_return_one_when_the_linter_found_no_file_to_lint(
        self,
        tmp_path: Path,
        fake_docker: list[tuple[str, Path]],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        upstream = make_upstream(tmp_path / "up", TEST_FLAG, [TEST_GOOD_FILE, TEST_BAD_FILE])
        plan = make_plan(tmp_path / "plan.json", [TEST_FLAG])
        monkeypatch.setattr(smoke, "run_image", lambda image, repo, flags: None)

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 1
        assert "FAIL (not-linted)" in capsys.readouterr().out

    def test_main_should_report_no_fixture_without_failing_when_the_flag_has_no_fixture_directory(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", TEST_FLAG, [TEST_GOOD_FILE])
        plan = make_plan(tmp_path / "plan.json", ["SOMETHING_ELSE"])

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 0
        assert "| SOMETHING_ELSE | no fixture | no fixture |" in capsys.readouterr().out

    def test_main_should_not_fail_when_a_fixture_directory_has_no_bad_file(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", TEST_FLAG, [TEST_GOOD_FILE])
        plan = make_plan(tmp_path / "plan.json", [TEST_FLAG])

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 0
        assert "| YAML | ok | no bad file |" in capsys.readouterr().out

    def test_main_should_put_workflow_fixtures_under_the_workflows_directory_when_the_flag_is_github_actions(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "GITHUB_ACTIONS", ["actions_good_01.yml", "actions_bad_01.yml"])
        plan = make_plan(tmp_path / "plan.json", ["GITHUB_ACTIONS"])

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 0
        for _flag, repo in fake_docker:
            assert list((repo / ".github" / "workflows").glob("actions_*.yml"))

    def test_main_should_copy_the_upstream_editorconfig_when_the_flag_is_editorconfig(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "EDITORCONFIG", ["x_good_1.ext", "x_bad_1.ext"])
        plan = make_plan(tmp_path / "plan.json", ["EDITORCONFIG"])

        code = smoke.main([TEST_IMAGE, str(plan), str(upstream)])

        assert code == 0
        for _flag, repo in fake_docker:
            assert (repo / ".editorconfig").read_text() == TEST_EDITORCONFIG

    def test_main_should_return_two_when_the_plan_cannot_be_read(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing_plan = tmp_path / "missing.json"

        code = smoke.main([TEST_IMAGE, str(missing_plan), str(tmp_path)])

        assert code == 2
        assert "cannot read the flags" in capsys.readouterr().out


class TestSubprocessWrappers:
    def test_init_repository_should_create_a_git_repository_when_git_is_available(self, tmp_path: Path) -> None:
        write(tmp_path / "a.yml")

        smoke.init_repository(tmp_path)

        assert (tmp_path / ".git").is_dir()

    def test_run_image_should_not_raise_when_the_container_exits_non_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[tuple[list[str], bool]] = []

        def fake_run(command: list[str], check: bool, capture_output: bool) -> subprocess.CompletedProcess[bytes]:
            seen.append((command, check))
            return subprocess.CompletedProcess(command, 1)

        monkeypatch.setattr(smoke.subprocess, "run", fake_run)

        smoke.run_image(TEST_IMAGE, tmp_path, [TEST_FLAG])

        assert seen[0][0][-1] == TEST_IMAGE
        assert seen[0][1] is False

    def test_clear_directory_should_remove_the_files_from_inside_the_image_when_the_directory_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        work = tmp_path / "work"
        write(work / "x" / "y.txt")
        commands: list[list[str]] = []

        def fake_run(command: list[str], check: bool, capture_output: bool) -> subprocess.CompletedProcess[bytes]:
            commands.append(command)
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(smoke.subprocess, "run", fake_run)

        smoke.clear_directory(TEST_IMAGE, work)

        assert f"{work}:/work" in commands[0]
        assert not work.exists()
