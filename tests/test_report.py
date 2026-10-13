"""Tests for superlint_lean.report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from superlint_lean import cli, report
from tests.shared import write_jsonl


def row(
    variant: str,
    pull_s: float | None = None,
    mode: str | None = "cold",
    runner: str | None = "github-hosted",
    **extra: Any,
) -> dict[str, Any]:
    data: dict[str, Any] = {"variant": variant, "runner": runner, "mode": mode, **extra}
    if pull_s is not None:
        data["pull_s"] = pull_s
    if mode is None or runner is None:
        data = {k: v for k, v in data.items() if v is not None}
    return data


def sizes(variant: str, pull_s: float, uncompressed_mb: int, compressed_mb: int) -> dict[str, Any]:
    return row(
        variant,
        pull_s,
        uncompressed_bytes=uncompressed_mb * report.MIB,
        compressed_bytes=compressed_mb * report.MIB,
    )


class TestNumbers:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0.5, 1.0), (1.5, 2.0), (2.5, 3.0), (-0.5, -1.0), (-2.4, -2.0), (0.4, 0.0)],
    )
    def test_round_half_away_should_round_halves_away_from_zero_when_the_value_is_a_half(
        self, value: float, expected: float
    ) -> None:
        assert report.round_half_away(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(70.0, "70"), (65.5, "65.5"), (0.0, "0"), (-0.0, "-0"), (-3.0, "-3")],
    )
    def test_number_should_print_like_jq_when_the_value_is_whole_or_negative_zero(
        self, value: float, expected: str
    ) -> None:
        assert report.number(value) == expected

    def test_median_should_return_none_when_there_are_no_values(self) -> None:
        assert report.median([]) is None

    def test_median_should_average_the_middle_pair_when_the_count_is_even(self) -> None:
        assert report.median([4.0, 1.0, 3.0, 2.0]) == 2.5

    def test_median_should_return_the_middle_value_when_the_count_is_odd(self) -> None:
        assert report.median([9.0, 1.0, 5.0]) == 5.0

    def test_seconds_should_print_one_decimal_and_na_when_the_value_is_missing(self) -> None:
        assert report.seconds(65.46) == "65.5 s"
        assert report.seconds(70.0) == "70 s"
        assert report.seconds(None) == "n/a"

    def test_percent_saved_should_be_na_when_the_baseline_is_missing_or_zero(self) -> None:
        assert report.percent_saved(None, 5) == "n/a"
        assert report.percent_saved(0, 5) == "n/a"
        assert report.percent_saved(1000, 150) == "85%"

    def test_drift_should_warn_when_the_change_exceeds_fifteen_percent(self) -> None:
        assert report.drift(100.0, 120.0) == "WARN 20%"
        assert report.drift(100.0, 110.0) == "10%"

    def test_drift_should_print_negative_zero_when_the_change_is_a_tiny_decrease(self) -> None:
        assert report.drift(1000.0, 999.0) == "-0%"

    def test_ratio_should_be_na_when_the_denominator_is_zero(self) -> None:
        assert report.ratio(70.0, 0.0) == "n/a"
        assert report.ratio(70.0, 10.0) == "7x"
        assert report.ratio(70.0, 9.0) == "7.8x"


class TestCompare:
    def test_compare_should_summarise_a_profile_when_all_variants_have_cold_runs(self) -> None:
        rows = [
            sizes("p/baseline", 70.0, 4000, 1300),
            sizes("p/baseline", 74.0, 4000, 1300),
            sizes("p/lean-gzip", 10.0, 500, 150),
            sizes("p/lean-zstd", 8.0, 500, 140),
            row("p/baseline-end", 72.0),
            row("p/lean-gzip", 80.0, mode="build"),
            row("p/lean-zstd", 8.0, mode="build"),
        ]

        lines = report.compare(rows)

        assert (
            "| p | 72 s | 10 s | 8 s | 7.2x | 9x | 4000 MB | 500 MB | 88% | 1300 MB | 150 MB | 88% | 0% | 80 s | 8 s |"
            in lines
        )

    def test_compare_should_print_na_when_a_variant_has_no_runs(self) -> None:
        rows = [sizes("p/lean-gzip", 10.0, 500, 150)]

        lines = report.compare(rows)

        assert (
            "| p | n/a | 10 s | n/a | n/a | n/a | n/a | 500 MB | n/a | n/a | 150 MB | n/a | n/a | n/a | n/a |" in lines
        )

    def test_compare_should_list_profiles_alphabetically_when_rows_arrive_unordered(self) -> None:
        rows = [row("zeta/baseline", 1.0), row("alpha/baseline", 1.0)]

        cold = report.compare(rows)[4:6]

        assert cold[0].startswith("| alpha |")
        assert cold[1].startswith("| zeta |")

    def test_compare_should_fill_the_warm_table_with_pull_and_start_when_warm_rows_exist(self) -> None:
        rows = [
            row("p/baseline", 1.4, mode="warm", start_s=0.4),
            row("p/lean-gzip", 0.9, mode="warm", start_s=0.3),
            row("p/lean-gzip", 1.1, mode="warm", start_s=None),
        ]

        lines = report.compare(rows)

        assert lines[-1] == "| p | 1.4 s | 1 s | 0.4 s | 0.3 s |"

    def test_compare_should_treat_a_row_without_mode_as_cold_when_mode_is_missing(self) -> None:
        rows = [row("p/baseline", 70.0, mode=None), row("p/lean-gzip", 10.0, mode=None)]

        lines = report.compare(rows)

        assert any(line.startswith("| p | 70 s | 10 s |") for line in lines)


class TestSummarize:
    def test_summarize_should_group_by_runner_mode_and_variant_when_rows_differ(self) -> None:
        rows = [
            sizes("p/baseline", 70.0, 4000, 1300),
            sizes("p/baseline", 74.0, 4000, 1300),
            row("p/baseline", 1.0, mode="warm", start_s=0.4),
        ]

        lines = report.summarize(rows)

        assert (
            lines[2]
            == "| github-hosted | cold | p/baseline | 2 | 72 s | 70 s-74 s | n/a | n/a | n/a | 1300 MB | 4000 MB |"
        )
        assert lines[3].startswith("| github-hosted | warm | p/baseline | 1 | 1 s | 1 s-1 s | 0.4 s |")

    def test_summarize_should_print_null_first_when_a_row_has_no_runner(self) -> None:
        rows = [row("p/lean-gzip", 80.0, mode="build", runner=None), sizes("p/baseline", 70.0, 4000, 1300)]

        lines = report.summarize(rows)

        assert lines[2].startswith("| null | build | p/lean-gzip | 1 | 80 s |")
        assert lines[3].startswith("| github-hosted | cold | p/baseline |")


class TestMain:
    def test_main_compare_should_print_the_tables_when_the_file_is_readable(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bench.jsonl"
        write_jsonl(path, [sizes("p/baseline", 70.0, 4000, 1300), sizes("p/lean-gzip", 10.0, 500, 150)])

        code = report.main_compare([str(path)])

        assert code == 0
        assert "### Cold pull (image removed before each pull)" in capsys.readouterr().out

    def test_main_summarize_should_ignore_blank_lines_when_the_file_has_them(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bench.jsonl"
        write_jsonl(path, [sizes("p/baseline", 70.0, 4000, 1300)])
        path.write_text(path.read_text() + "\n\n")

        code = report.main_summarize([str(path)])

        assert code == 0
        assert "| github-hosted | cold | p/baseline | 1 |" in capsys.readouterr().out

    def test_main_compare_should_return_two_when_no_file_is_given(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = report.main_compare([])

        assert code == 2
        assert "usage: superlint-lean compare" in capsys.readouterr().out

    def test_main_compare_should_return_two_when_the_file_does_not_exist(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = report.main_compare([str(tmp_path / "missing.jsonl")])

        assert code == 2
        assert "cannot read the results" in capsys.readouterr().out

    def test_main_compare_should_return_two_when_a_line_is_not_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bad.jsonl"
        path.write_text("not json\n")

        code = report.main_summarize([str(path)])

        assert code == 2
        assert "cannot read the results" in capsys.readouterr().out

    def test_cli_should_dispatch_compare_and_summarize_when_the_commands_are_given(self, tmp_path: Path) -> None:
        path = tmp_path / "bench.jsonl"
        write_jsonl(path, [sizes("p/baseline", 70.0, 4000, 1300)])

        assert cli.main(["compare", str(path)]) == 0
        assert cli.main(["summarize", str(path)]) == 0
