"""Tests for superlint_lean.report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from superlint_lean import cli, report
from tests.shared import write_jsonl

TEST_PROFILE = "p"
TEST_RUNNER = "github-hosted"
TEST_BASELINE = f"{TEST_PROFILE}/baseline"
TEST_BASELINE_END = f"{TEST_PROFILE}/baseline-end"
TEST_GZIP = f"{TEST_PROFILE}/lean-gzip"
TEST_ZSTD = f"{TEST_PROFILE}/lean-zstd"


def row(
    variant: str,
    pull_s: float | None = None,
    mode: str | None = "cold",
    runner: str | None = TEST_RUNNER,
    **extra: Any,
) -> dict[str, Any]:
    data: dict[str, Any] = {"variant": variant, "runner": runner, "mode": mode, **extra}
    if pull_s is not None:
        data["pull_s"] = pull_s
    return {key: value for key, value in data.items() if value is not None or key in extra}


def sizes(variant: str, pull_s: float, uncompressed_mb: int, compressed_mb: int) -> dict[str, Any]:
    return row(
        variant,
        pull_s,
        uncompressed_bytes=uncompressed_mb * report.MIB,
        compressed_bytes=compressed_mb * report.MIB,
    )


def first_cells(lines: list[str]) -> list[str]:
    return [line.split("|")[1].strip() for line in lines]


class TestRoundHalfAway:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0.5, 1.0), (1.5, 2.0), (2.5, 3.0), (-0.5, -1.0), (-2.4, -2.0), (0.4, 0.0)],
    )
    def test_round_half_away_should_round_halves_away_from_zero_when_the_value_is_a_half(
        self, value: float, expected: float
    ) -> None:
        rounded = report.round_half_away(value)

        assert rounded == expected


class TestNumber:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(70.0, "70"), (65.5, "65.5"), (0.0, "0"), (-0.0, "-0"), (-3.0, "-3")],
    )
    def test_number_should_print_like_jq_when_the_value_is_whole_or_negative_zero(
        self, value: float, expected: str
    ) -> None:
        text = report.number(value)

        assert text == expected


class TestMedian:
    def test_median_should_return_none_when_there_are_no_values(self) -> None:
        result = report.median([])

        assert result is None

    def test_median_should_average_the_middle_pair_when_the_count_is_even(self) -> None:
        result = report.median([4.0, 1.0, 3.0, 2.0])

        assert result == 2.5

    def test_median_should_return_the_middle_value_when_the_count_is_odd(self) -> None:
        result = report.median([9.0, 1.0, 5.0])

        assert result == 5.0


class TestSeconds:
    @pytest.mark.parametrize(("value", "expected"), [(65.46, "65.5 s"), (70.0, "70 s")])
    def test_seconds_should_print_one_decimal_when_the_value_is_a_number(self, value: float, expected: str) -> None:
        text = report.seconds(value)

        assert text == expected

    def test_seconds_should_print_na_when_the_value_is_missing(self) -> None:
        text = report.seconds(None)

        assert text == "n/a"


class TestPercentSaved:
    @pytest.mark.parametrize(("before", "after"), [(None, 5), (0, 5), (1000, None)])
    def test_percent_saved_should_be_na_when_a_size_is_missing_or_the_baseline_is_zero(
        self, before: int | None, after: int | None
    ) -> None:
        text = report.percent_saved(before, after)

        assert text == "n/a"

    def test_percent_saved_should_print_the_rounded_saving_when_both_sizes_are_known(self) -> None:
        text = report.percent_saved(1000, 150)

        assert text == "85%"


class TestDrift:
    @pytest.mark.parametrize(
        ("first", "last", "expected"),
        [(100.0, 120.0, "WARN 20%"), (100.0, 110.0, "10%"), (1000.0, 999.0, "-0%")],
        ids=["above-fifteen", "below-fifteen", "tiny-decrease"],
    )
    def test_drift_should_warn_only_above_fifteen_percent_when_the_baseline_moves(
        self, first: float, last: float, expected: str
    ) -> None:
        text = report.drift(first, last)

        assert text == expected

    def test_drift_should_be_na_when_a_reading_is_missing(self) -> None:
        text = report.drift(None, 100.0)

        assert text == "n/a"


class TestRatio:
    def test_ratio_should_be_na_when_the_denominator_is_zero(self) -> None:
        text = report.ratio(70.0, 0.0)

        assert text == "n/a"

    @pytest.mark.parametrize(("numerator", "denominator", "expected"), [(70.0, 10.0, "7x"), (70.0, 9.0, "7.8x")])
    def test_ratio_should_print_one_decimal_when_both_values_are_known(
        self, numerator: float, denominator: float, expected: str
    ) -> None:
        text = report.ratio(numerator, denominator)

        assert text == expected


class TestCompare:
    def test_compare_should_summarise_a_profile_when_all_variants_have_cold_runs(self) -> None:
        rows = [
            sizes(TEST_BASELINE, 70.0, 4000, 1300),
            sizes(TEST_BASELINE, 74.0, 4000, 1300),
            sizes(TEST_GZIP, 10.0, 500, 150),
            sizes(TEST_ZSTD, 8.0, 500, 140),
            row(TEST_BASELINE_END, 72.0),
            row(TEST_GZIP, 80.0, mode="build"),
            row(TEST_ZSTD, 8.0, mode="build"),
        ]

        lines = report.compare(rows)

        expected = (
            "| p | 72 s | 10 s | 8 s | 7.2x | 9x | 4000 MB | 500 MB | 88% | 1300 MB | 150 MB | 88% | 0% | 80 s | 8 s |"
        )
        assert expected in lines

    def test_compare_should_print_na_when_a_variant_has_no_runs(self) -> None:
        rows = [sizes(TEST_GZIP, 10.0, 500, 150)]

        lines = report.compare(rows)

        expected = "| p | n/a | 10 s | n/a | n/a | n/a | n/a | 500 MB | n/a | n/a | 150 MB | n/a | n/a | n/a | n/a |"
        assert expected in lines

    def test_compare_should_list_profiles_alphabetically_when_rows_arrive_unordered(self) -> None:
        rows = [row("zeta/baseline", 1.0), row("alpha/baseline", 1.0)]

        lines = report.compare(rows)

        assert first_cells(lines[4:6]) == ["alpha", "zeta"]

    def test_compare_should_fill_the_warm_table_with_pull_and_start_when_warm_rows_exist(self) -> None:
        rows = [
            row(TEST_BASELINE, 1.4, mode="warm", start_s=0.4),
            row(TEST_GZIP, 0.9, mode="warm", start_s=0.3),
            row(TEST_GZIP, 1.1, mode="warm", start_s=None),
        ]

        lines = report.compare(rows)

        assert lines[-1] == "| p | 1.4 s | 1 s | 0.4 s | 0.3 s |"

    def test_compare_should_treat_a_row_without_mode_as_cold_when_mode_is_missing(self) -> None:
        rows = [row(TEST_BASELINE, 70.0, mode=None), row(TEST_GZIP, 10.0, mode=None)]

        lines = report.compare(rows)

        assert any(line.startswith("| p | 70 s | 10 s |") for line in lines)


class TestSummarize:
    def test_summarize_should_group_by_runner_mode_and_variant_when_rows_differ(self) -> None:
        rows = [
            sizes(TEST_BASELINE, 70.0, 4000, 1300),
            sizes(TEST_BASELINE, 74.0, 4000, 1300),
            row(TEST_BASELINE, 1.0, mode="warm", start_s=0.4),
        ]

        lines = report.summarize(rows)

        assert (
            lines[2]
            == "| github-hosted | cold | p/baseline | 2 | 72 s | 70 s-74 s | n/a | n/a | n/a | 1300 MB | 4000 MB |"
        )
        assert lines[3].startswith("| github-hosted | warm | p/baseline | 1 | 1 s | 1 s-1 s | 0.4 s |")

    def test_summarize_should_print_null_first_when_a_row_has_no_runner(self) -> None:
        rows = [row(TEST_GZIP, 80.0, mode="build", runner=None), sizes(TEST_BASELINE, 70.0, 4000, 1300)]

        lines = report.summarize(rows)

        assert first_cells(lines[2:4]) == ["null", TEST_RUNNER]


class TestMain:
    def test_main_compare_should_print_the_tables_when_the_file_is_readable(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bench.jsonl"
        write_jsonl(path, [sizes(TEST_BASELINE, 70.0, 4000, 1300), sizes(TEST_GZIP, 10.0, 500, 150)])

        code = report.main_compare([str(path)])

        assert code == 0
        assert "### Cold pull (image removed before each pull)" in capsys.readouterr().out

    def test_main_summarize_should_ignore_blank_lines_when_the_file_has_them(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bench.jsonl"
        write_jsonl(path, [sizes(TEST_BASELINE, 70.0, 4000, 1300)])
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
        missing_file = tmp_path / "missing.jsonl"

        code = report.main_compare([str(missing_file)])

        assert code == 2
        assert "cannot read the results" in capsys.readouterr().out

    def test_main_summarize_should_return_two_when_a_line_is_not_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "bad.jsonl"
        path.write_text("not json\n")

        code = report.main_summarize([str(path)])

        assert code == 2
        assert "cannot read the results" in capsys.readouterr().out

    @pytest.mark.parametrize("command", ["compare", "summarize"])
    def test_cli_should_dispatch_the_report_command_when_it_is_given(self, command: str, tmp_path: Path) -> None:
        path = tmp_path / "bench.jsonl"
        write_jsonl(path, [sizes(TEST_BASELINE, 70.0, 4000, 1300)])

        code = cli.main([command, str(path)])

        assert code == 0
