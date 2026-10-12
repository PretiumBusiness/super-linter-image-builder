"""Tests for superlint_lean.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from superlint_lean import config as slconfig
from tests.shared import WORKFLOW_FIXTURE


class TestEffectiveFlags:
    def test_effective_flags_should_enable_everything_when_no_validate_variable_is_set(
        self, upstream_flags: set[str]
    ) -> None:
        flags = slconfig.effective_flags({}, upstream_flags)

        assert set(flags) == upstream_flags

    def test_effective_flags_should_return_only_true_flags_when_some_are_true(self, upstream_flags: set[str]) -> None:
        env = {"VALIDATE_YAML": "true", "VALIDATE_JSON": "true"}

        flags = slconfig.effective_flags(env, upstream_flags)

        assert flags == ["JSON", "YAML"]

    def test_effective_flags_should_remove_false_flags_when_only_false_flags_are_set(
        self, upstream_flags: set[str]
    ) -> None:
        env = {"VALIDATE_YAML": "false"}

        flags = slconfig.effective_flags(env, upstream_flags)

        assert set(flags) == upstream_flags - {"YAML"}

    def test_effective_flags_should_raise_when_true_and_false_are_mixed(self, upstream_flags: set[str]) -> None:
        env = {"VALIDATE_YAML": "true", "VALIDATE_JSON": "false"}

        with pytest.raises(slconfig.ConfigError, match="mix true and false"):
            slconfig.effective_flags(env, upstream_flags)

    def test_effective_flags_should_ignore_all_codebase_when_it_is_the_only_other_variable(
        self, upstream_flags: set[str]
    ) -> None:
        env = {"VALIDATE_ALL_CODEBASE": "true", "VALIDATE_YAML": "true"}

        flags = slconfig.effective_flags(env, upstream_flags)

        assert flags == ["YAML"]

    def test_effective_flags_should_raise_when_value_is_not_a_boolean(self, upstream_flags: set[str]) -> None:
        env = {"VALIDATE_YAML": "yes"}

        with pytest.raises(slconfig.ConfigError, match="must be true or false"):
            slconfig.effective_flags(env, upstream_flags)


class TestParseEnvText:
    def test_parse_env_text_should_strip_quotes_when_values_are_quoted(self) -> None:
        text = "VALIDATE_YAML=true\nLINTER_RULES_PATH=\".github/linters\"\nOTHER='x'\n"

        parsed = slconfig.parse_env_text(text)

        assert parsed == {"VALIDATE_YAML": "true", "LINTER_RULES_PATH": ".github/linters", "OTHER": "x"}

    def test_parse_env_text_should_skip_comments_and_blank_lines_when_text_has_them(self) -> None:
        text = "# comment\n\nVALIDATE_JSON=true\n"

        parsed = slconfig.parse_env_text(text)

        assert parsed == {"VALIDATE_JSON": "true"}

    def test_parse_env_files_should_let_later_files_win_when_a_key_repeats(self, tmp_path: Path) -> None:
        first = tmp_path / "first.env"
        second = tmp_path / "second.env"
        first.write_text("VALIDATE_YAML=false\nA=1\n")
        second.write_text("VALIDATE_YAML=true\n")

        parsed = slconfig.parse_env_files([first, second])

        assert parsed == {"VALIDATE_YAML": "true", "A": "1"}


class TestParseWorkflow:
    def test_parse_workflow_should_read_step_env_when_workflow_has_a_super_linter_step(self) -> None:
        env = slconfig.parse_workflow(WORKFLOW_FIXTURE)

        assert env["VALIDATE_PYTHON_RUFF"] == "true"
        assert env["LINTER_RULES_PATH"] == ".github/linters"

    def test_parse_workflow_should_merge_workflow_job_and_step_env_when_all_define_values(self, tmp_path: Path) -> None:
        workflow = tmp_path / "w.yml"
        workflow.write_text(
            "env:\n  A: workflow\n  B: workflow\n"
            "jobs:\n  lint:\n    env:\n      B: job\n      C: job\n    steps:\n"
            "      - uses: super-linter/super-linter@v9\n        env:\n          C: step\n"
        )

        env = slconfig.parse_workflow(workflow)

        assert env == {"A": "workflow", "B": "job", "C": "step"}

    def test_parse_workflow_should_raise_when_no_super_linter_step_exists(self, tmp_path: Path) -> None:
        workflow = tmp_path / "w.yml"
        workflow.write_text("jobs:\n  build:\n    steps:\n      - run: echo hi\n")

        with pytest.raises(slconfig.ConfigError, match="no super-linter"):
            slconfig.parse_workflow(workflow)
