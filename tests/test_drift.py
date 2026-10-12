"""Tests for superlint_lean.drift."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from superlint_lean import config as slconfig
from superlint_lean import drift
from tests.shared import WORKFLOW_FIXTURE


def findings_by_file(
    env: dict[str, str],
    files: list[str],
    upstream_flags: set[str],
    filetypes: dict[str, Any],
    **kwargs: Any,
) -> dict[str, list[str]]:
    return {item["file"]: item["flags"] for item in drift.check(env, files, upstream_flags, filetypes, **kwargs)}


@pytest.fixture
def ghwm_env() -> dict[str, str]:
    return slconfig.parse_workflow(WORKFLOW_FIXTURE)


class TestCheck:
    def test_check_should_report_nothing_when_changed_files_are_covered(
        self, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        files = ["src/a.py", "README.md", "package.json", ".github/workflows/x.yml", "conf.yaml", "notes.txt"]

        findings = findings_by_file(ghwm_env, files, upstream_flags, filetypes)

        assert findings == {}

    def test_check_should_flag_files_when_their_linters_are_not_enabled(
        self, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        files = ["src/main.rs", "web/app.ts", "Dockerfile", "ci/build.sh"]

        findings = findings_by_file(ghwm_env, files, upstream_flags, filetypes)

        assert set(findings) == set(files)
        assert "RUST_2024" in findings["src/main.rs"]
        assert "DOCKERFILE_HADOLINT" in findings["Dockerfile"]

    def test_check_should_skip_files_when_they_match_the_exclude_regex(
        self, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        files = [".agents/tool.rs", "x/skills-lock.json.rs"]

        findings = findings_by_file(ghwm_env, files, upstream_flags, filetypes)

        assert findings == {}

    def test_check_should_skip_files_when_they_do_not_match_the_include_regex(
        self, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        env = {**ghwm_env, "FILTER_REGEX_INCLUDE": ".*src/.*"}

        findings = findings_by_file(env, ["src/a.rs", "other/b.rs"], upstream_flags, filetypes)

        assert set(findings) == {"src/a.rs"}

    def test_check_should_skip_files_when_their_extension_is_allowed(
        self, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        findings = findings_by_file(ghwm_env, ["a.rs"], upstream_flags, filetypes, allow_ext=("rs",))

        assert findings == {}

    def test_check_should_skip_files_when_their_name_is_allowed(
        self, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        findings = findings_by_file(ghwm_env, ["ci/Dockerfile"], upstream_flags, filetypes, allow_ext=("dockerfile",))

        assert findings == {}

    def test_check_should_use_the_shebang_when_a_script_has_no_extension(
        self, tmp_path: Path, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        (tmp_path / "bin").mkdir()
        (tmp_path / "bin" / "run").write_text("#!/usr/bin/env bash\necho hi\n")
        (tmp_path / "bin" / "tool").write_text("#!/usr/bin/env python3\nprint(1)\n")

        findings = findings_by_file(ghwm_env, ["bin/run", "bin/tool"], upstream_flags, filetypes, root=str(tmp_path))

        assert set(findings) == {"bin/run"}

    def test_check_should_treat_a_missing_script_as_covered_when_the_file_cannot_be_read(
        self, tmp_path: Path, ghwm_env: dict[str, str], upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        findings = findings_by_file(ghwm_env, ["bin/gone"], upstream_flags, filetypes, root=str(tmp_path))

        assert findings == {}

    def test_check_should_need_zizmor_when_the_file_is_a_dependabot_config(
        self, upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        yaml_only = {"VALIDATE_YAML": "true"}
        json_only = {"VALIDATE_JSON": "true"}
        files = [".github/dependabot.yml"]

        covered = findings_by_file(yaml_only, files, upstream_flags, filetypes)
        flagged = findings_by_file(json_only, files, upstream_flags, filetypes)

        assert covered == {}
        assert ".github/dependabot.yml" in flagged


class TestFiletypesTable:
    def test_filetypes_table_should_only_use_mapped_flags_when_rules_are_loaded(
        self, upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        used_flags = {flag for rule in filetypes["rules"] for flag in rule["flags"]}

        assert used_flags - upstream_flags == set()

    def test_filetypes_table_should_only_list_mapped_always_on_flags_when_loaded(
        self, upstream_flags: set[str], filetypes: dict[str, Any]
    ) -> None:
        assert set(filetypes["always_on"]) - upstream_flags == set()


class TestChangedFiles:
    def test_changed_files_should_list_added_and_modified_files_when_base_is_a_valid_ref(self, tmp_path: Path) -> None:
        git(tmp_path, "init", "-q", "-b", "main")
        (tmp_path / "a.txt").write_text("a")
        git(tmp_path, "add", ".")
        git(tmp_path, "commit", "-q", "-m", "init")
        git(tmp_path, "checkout", "-q", "-b", "topic")
        (tmp_path / "b.txt").write_text("b")
        git(tmp_path, "add", ".")
        git(tmp_path, "commit", "-q", "-m", "add b")

        files = drift.changed_files("main", str(tmp_path))

        assert files == ["b.txt"]

    def test_changed_files_should_raise_when_base_ref_does_not_exist(self, tmp_path: Path) -> None:
        git(tmp_path, "init", "-q", "-b", "main")

        with pytest.raises(slconfig.ConfigError, match="git diff against"):
            drift.changed_files("origin/nope", str(tmp_path))


def git(root: Path, *args: str) -> None:
    command = [
        "git",
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.com",
        "-C",
        str(root),
        *args,
    ]
    subprocess.run(command, check=True, capture_output=True)


class TestMain:
    def test_main_should_return_one_when_files_are_not_covered(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        changed = tmp_path / "changed.txt"
        changed.write_text("src/main.rs\n")

        code = drift.main(["--workflow", str(WORKFLOW_FIXTURE), "--files-from", str(changed)])

        assert code == 1
        assert "::error file=src/main.rs::" in capsys.readouterr().out

    def test_main_should_return_zero_when_warn_only_is_set(self, tmp_path: Path) -> None:
        changed = tmp_path / "changed.txt"
        changed.write_text("src/main.rs\n")

        code = drift.main(["--workflow", str(WORKFLOW_FIXTURE), "--files-from", str(changed), "--warn-only"])

        assert code == 0

    def test_main_should_write_report_when_report_path_is_given(self, tmp_path: Path) -> None:
        changed = tmp_path / "changed.txt"
        changed.write_text("README.md\n")
        report = tmp_path / "report.md"

        code = drift.main(["--workflow", str(WORKFLOW_FIXTURE), "--files-from", str(changed), "--report", str(report)])

        assert code == 0
        assert "0 not covered" in report.read_text()

    def test_main_should_return_two_when_no_configuration_is_given(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = drift.main(["--base", "origin/main"])

        assert code == 2
        assert "give --workflow or --env" in capsys.readouterr().out

    def test_main_should_return_two_when_neither_base_nor_file_list_is_given(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = drift.main(["--workflow", str(WORKFLOW_FIXTURE)])

        assert code == 2
        assert "give --base or --files-from" in capsys.readouterr().out
