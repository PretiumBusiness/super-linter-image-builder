"""Tests for superlint_lean.smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from superlint_lean import smoke

SUMMARY_PASS = "| Language | Validation result |\n| --- | --- |\n| YAML     | Pass ✅           |\n"
SUMMARY_FAIL = "| Language | Validation result |\n| --- | --- |\n| YAML     | Fail ❌           |\n"


def write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def make_upstream(root: Path, flag: str, files: list[str]) -> Path:
    fixtures = root / "test" / "linters" / flag.lower()
    for name in files:
        write(fixtures / name)
    write(root / ".editorconfig", "root = true\n")
    return root


def make_plan(path: Path, flags: list[str]) -> Path:
    path.write_text(json.dumps({"flags": flags}))
    return path


@pytest.fixture
def fake_docker(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Path]]:
    """Replace git and docker; the fake image 'lints' by writing a summary: Fail when a bad file is present."""
    calls: list[tuple[str, Path]] = []

    def fake_run_image(image: str, repo: Path, flag: str) -> None:
        calls.append((flag, repo))
        bad = any("bad" in p.name for p in repo.rglob("*") if p.is_file())
        write(repo / smoke.SUMMARY, (SUMMARY_FAIL if bad else SUMMARY_PASS).replace("YAML    ", f"{flag:<8}"))

    monkeypatch.setattr(smoke, "init_repository", lambda repo: None)
    monkeypatch.setattr(smoke, "run_image", fake_run_image)
    monkeypatch.setattr(smoke, "clear_directory", lambda image, work: None)
    return calls


class TestVerdict:
    def test_verdict_should_return_pass_when_the_summary_row_says_pass(self) -> None:
        assert smoke.verdict(SUMMARY_PASS, "YAML") == smoke.CLEAN

    def test_verdict_should_return_fail_when_the_summary_row_says_fail(self) -> None:
        assert smoke.verdict(SUMMARY_FAIL, "YAML") == smoke.ERRORS

    def test_verdict_should_return_not_linted_when_the_flag_is_not_in_the_summary(self) -> None:
        assert smoke.verdict(SUMMARY_PASS, "JSON") == smoke.NOT_LINTED

    def test_verdict_should_not_match_a_longer_flag_name_when_it_shares_the_prefix(self) -> None:
        summary = "| GITHUB_ACTIONS_ZIZMOR | Pass ✅ |\n"

        assert smoke.verdict(summary, "GITHUB_ACTIONS") == smoke.NOT_LINTED


class TestCopyFixtures:
    def test_copy_fixtures_should_copy_only_files_with_the_kind_in_their_path_when_both_kinds_exist(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "src"
        write(source / "a_good_1.yml")
        write(source / "a_bad_1.yml")
        write(source / "bad" / "nested.txt")

        copied = smoke.copy_fixtures(source, "bad", tmp_path / "dest")

        assert copied == 2
        assert sorted(p.name for p in (tmp_path / "dest").rglob("*") if p.is_file()) == ["a_bad_1.yml", "nested.txt"]

    def test_copy_fixtures_should_return_zero_when_no_file_matches(self, tmp_path: Path) -> None:
        source = tmp_path / "src"
        write(source / "a_good_1.yml")

        assert smoke.copy_fixtures(source, "bad", tmp_path / "dest") == 0


class TestDestination:
    @pytest.mark.parametrize("flag", ["GITHUB_ACTIONS", "GITHUB_ACTIONS_ZIZMOR"])
    def test_destination_should_use_the_workflows_directory_when_the_flag_lints_workflows(
        self, flag: str, tmp_path: Path
    ) -> None:
        assert smoke.destination(tmp_path, flag) == tmp_path / ".github" / "workflows"

    def test_destination_should_use_the_repository_root_when_the_flag_lints_any_file(self, tmp_path: Path) -> None:
        assert smoke.destination(tmp_path, "YAML") == tmp_path


class TestDockerCommand:
    def test_docker_command_should_enable_only_the_given_flag_and_mount_the_repository(self, tmp_path: Path) -> None:
        command = smoke.docker_command("img:1", tmp_path, "YAML")

        assert "VALIDATE_YAML=true" in command
        assert f"{tmp_path}:/tmp/lint" in command
        assert command[-1] == "img:1"
        assert sum(1 for part in command if part.startswith("VALIDATE_") and part != "VALIDATE_ALL_CODEBASE=true") == 1


class TestMain:
    def test_main_should_return_zero_and_print_ok_when_good_passes_and_bad_fails(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "YAML", ["yml_good_1.yml", "yml_bad_1.yml"])
        plan = make_plan(tmp_path / "plan.json", ["YAML"])

        code = smoke.main(["img", str(plan), str(upstream)])

        assert code == 0
        assert "| YAML | ok | ok |" in capsys.readouterr().out
        assert [flag for flag, _ in fake_docker] == ["YAML", "YAML"]

    def test_main_should_return_one_when_the_bad_files_pass(
        self,
        tmp_path: Path,
        fake_docker: list[tuple[str, Path]],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "YAML", ["yml_good_1.yml", "yml_bad_1.yml"])
        plan = make_plan(tmp_path / "plan.json", ["YAML"])
        monkeypatch.setattr(smoke, "run_image", lambda image, repo, flag: write(repo / smoke.SUMMARY, SUMMARY_PASS))

        code = smoke.main(["img", str(plan), str(upstream)])

        assert code == 1
        assert "FAIL (pass)" in capsys.readouterr().out

    def test_main_should_return_one_when_the_linter_found_no_file_to_lint(
        self,
        tmp_path: Path,
        fake_docker: list[tuple[str, Path]],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "YAML", ["yml_good_1.yml", "yml_bad_1.yml"])
        plan = make_plan(tmp_path / "plan.json", ["YAML"])
        monkeypatch.setattr(smoke, "run_image", lambda image, repo, flag: None)

        code = smoke.main(["img", str(plan), str(upstream)])

        assert code == 1
        assert "FAIL (not-linted)" in capsys.readouterr().out

    def test_main_should_report_no_fixture_without_failing_when_the_flag_has_no_fixture_directory(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "YAML", ["yml_good_1.yml"])
        plan = make_plan(tmp_path / "plan.json", ["SOMETHING_ELSE"])

        code = smoke.main(["img", str(plan), str(upstream)])

        assert code == 0
        assert "| SOMETHING_ELSE | no fixture | no fixture |" in capsys.readouterr().out

    def test_main_should_not_fail_when_a_fixture_directory_has_no_bad_file(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "YAML", ["yml_good_1.yml"])
        plan = make_plan(tmp_path / "plan.json", ["YAML"])

        code = smoke.main(["img", str(plan), str(upstream)])

        assert code == 0
        assert "| YAML | ok | no bad file |" in capsys.readouterr().out

    def test_main_should_put_workflow_fixtures_under_the_workflows_directory_when_the_flag_is_github_actions(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "GITHUB_ACTIONS", ["actions_good_01.yml", "actions_bad_01.yml"])
        plan = make_plan(tmp_path / "plan.json", ["GITHUB_ACTIONS"])
        seen: list[bool] = []
        original = smoke.run_image

        def spy(image: str, repo: Path, flag: str) -> None:
            seen.append(any(p.parent == repo / ".github" / "workflows" for p in repo.rglob("*.yml")))
            original(image, repo, flag)

        smoke.run_image = spy  # type: ignore[assignment]
        try:
            code = smoke.main(["img", str(plan), str(upstream)])
        finally:
            smoke.run_image = original

        assert code == 0
        assert seen == [True, True]

    def test_main_should_copy_the_upstream_editorconfig_when_the_flag_is_editorconfig(
        self, tmp_path: Path, fake_docker: list[tuple[str, Path]]
    ) -> None:
        upstream = make_upstream(tmp_path / "up", "EDITORCONFIG", ["x_good_1.ext", "x_bad_1.ext"])
        plan = make_plan(tmp_path / "plan.json", ["EDITORCONFIG"])

        code = smoke.main(["img", str(plan), str(upstream)])

        assert code == 0
        assert all((repo / ".editorconfig").read_text() == "root = true\n" for _, repo in fake_docker)

    def test_main_should_return_two_when_the_plan_cannot_be_read(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = smoke.main(["img", str(tmp_path / "missing.json"), str(tmp_path)])

        assert code == 2
        assert "cannot read the flags" in capsys.readouterr().out


class TestSubprocessWrappers:
    def test_init_repository_should_commit_the_files_when_git_is_available(self, tmp_path: Path) -> None:
        write(tmp_path / "a.yml")

        smoke.init_repository(tmp_path)

        assert (tmp_path / ".git").is_dir()

    def test_run_image_should_not_raise_when_the_container_exits_non_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[tuple[list[str], bool]] = []

        def fake_run(command: list[str], check: bool, capture_output: bool) -> None:
            seen.append((command, check))

        monkeypatch.setattr(smoke.subprocess, "run", fake_run)

        smoke.run_image("img:1", tmp_path, "YAML")

        assert seen[0][0][-1] == "img:1"
        assert seen[0][1] is False

    def test_clear_directory_should_remove_the_files_from_inside_the_image_and_delete_the_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        work = tmp_path / "work"
        write(work / "x" / "y.txt")
        seen: list[list[str]] = []

        def fake_run(command: list[str], check: bool, capture_output: bool) -> None:
            seen.append(command)

        monkeypatch.setattr(smoke.subprocess, "run", fake_run)

        smoke.clear_directory("img:1", work)

        assert f"{work}:/work" in seen[0]
        assert not work.exists()
