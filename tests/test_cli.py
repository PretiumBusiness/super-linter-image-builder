"""Tests for superlint_lean.cli."""

from __future__ import annotations

import subprocess
import sys

import pytest

from superlint_lean import __version__, cli


class TestMain:
    def test_main_should_print_usage_and_return_zero_when_no_arguments_are_given(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main([])

        output = capsys.readouterr().out
        assert code == 0
        for command in cli.COMMANDS:
            assert command in output

    @pytest.mark.parametrize("flag", ["-h", "--help", "help"])
    def test_main_should_print_usage_when_a_help_flag_is_given(
        self, flag: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main([flag])

        assert code == 0
        assert "usage: superlint-lean" in capsys.readouterr().out

    def test_main_should_print_the_version_when_version_flag_is_given(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = cli.main(["--version"])

        assert code == 0
        assert capsys.readouterr().out.strip() == f"superlint-lean {__version__}"

    def test_main_should_return_two_when_the_command_is_unknown(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = cli.main(["frobnicate"])

        assert code == 2
        assert "unknown command 'frobnicate'" in capsys.readouterr().err

    def test_main_should_dispatch_to_the_command_when_it_is_known(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = cli.main(["drift", "--base", "origin/main"])

        assert code == 2
        assert "give --workflow or --env" in capsys.readouterr().out


class TestModuleEntryPoint:
    def test_module_entry_point_should_print_the_version_when_run_with_python_dash_m(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "superlint_lean", "--version"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0
        assert result.stdout.strip() == f"superlint-lean {__version__}"
