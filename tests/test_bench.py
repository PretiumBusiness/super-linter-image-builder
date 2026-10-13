"""Tests for superlint_lean.bench."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from superlint_lean import bench, cli

IMAGE = "ghcr.io/o/r/lean:v1"
MANIFEST = json.dumps({"layers": [{"size": 100}, {"size": 250}]})


class FakeDocker:
    """Stands in for bench.run: records commands and answers like docker and crane would."""

    def __init__(self, fail: tuple[str, ...] = (), manifest: str = MANIFEST) -> None:
        self.commands: list[list[str]] = []
        self.fail = fail
        self.manifest = manifest

    def __call__(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        self.commands.append(list(command))
        key = " ".join(command[:3])
        code = 1 if any(key.startswith(prefix) for prefix in self.fail) else 0
        if code and check:
            raise bench.BenchError(f"{key} failed: boom")
        out = ""
        if command[:3] == ["docker", "image", "inspect"]:
            out = "4096\n"
        elif command[:2] == ["crane", "manifest"]:
            out = self.manifest
        return subprocess.CompletedProcess(command, code, stdout=out, stderr="")

    def verbs(self) -> list[str]:
        return [" ".join(c[:3]) for c in self.commands]


@pytest.fixture
def docker(monkeypatch: pytest.MonkeyPatch) -> FakeDocker:
    fake = FakeDocker()
    monkeypatch.setattr(bench, "run", fake)
    monkeypatch.setattr(bench, "have_crane", lambda: True)
    clock = iter(float(n) * 0.5 for n in range(1000))
    monkeypatch.setattr(bench.time, "perf_counter", lambda: next(clock))
    return fake


class TestBench:
    def test_bench_should_clear_images_before_every_pull_when_the_mode_is_cold(
        self, docker: FakeDocker, tmp_path: Path
    ) -> None:
        bench.bench(IMAGE, 2, "p/lean-zstd", "github-hosted", "cold", tmp_path / "out.jsonl", split=False)

        verbs = docker.verbs()
        pulls = [i for i, v in enumerate(verbs) if v == "docker pull --quiet"]
        assert len(pulls) == 2
        for i in pulls:
            assert verbs[i - 3 : i] == ["docker image rm", "docker image prune", "docker builder prune"]

    def test_bench_should_pull_once_unmeasured_and_not_clear_when_the_mode_is_warm(
        self, docker: FakeDocker, tmp_path: Path
    ) -> None:
        rows = bench.bench(IMAGE, 2, "p/baseline", "self-hosted", "warm", tmp_path / "out.jsonl", split=False)

        verbs = docker.verbs()
        assert verbs.count("docker pull --quiet") == 3
        assert "docker image rm" not in verbs
        assert [r["mode"] for r in rows] == ["warm", "warm"]

    def test_bench_should_write_rows_with_the_expected_keys_and_append_them_to_the_file(
        self, docker: FakeDocker, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "out.jsonl"
        out.write_text('{"earlier": true}\n')

        bench.bench(IMAGE, 1, "p/lean-gzip", "github-hosted", "cold", out, split=False)

        lines = out.read_text().splitlines()
        row = json.loads(lines[1])
        assert lines[0] == '{"earlier": true}'
        assert list(row) == [
            "image",
            "variant",
            "runner",
            "mode",
            "run",
            "pull_s",
            "start_s",
            "download_s",
            "load_s",
            "compressed_bytes",
            "uncompressed_bytes",
        ]
        assert (row["compressed_bytes"], row["uncompressed_bytes"], row["download_s"]) == (350, 4096, None)
        assert capsys.readouterr().out.strip() == lines[1]

    def test_bench_should_time_the_pull_and_the_start_separately(self, docker: FakeDocker, tmp_path: Path) -> None:
        rows = bench.bench(IMAGE, 1, "p/lean-gzip", "r", "cold", tmp_path / "out.jsonl", split=False)

        assert rows[0]["pull_s"] == 0.5
        assert rows[0]["start_s"] == 0.5

    def test_bench_should_measure_download_and_load_when_split_is_on_in_cold_mode(
        self, docker: FakeDocker, tmp_path: Path
    ) -> None:
        rows = bench.bench(IMAGE, 1, "p/baseline", "r", "cold", tmp_path / "out.jsonl", split=True)

        assert rows[0]["download_s"] == 0.5
        assert rows[0]["load_s"] == 0.5
        assert "crane pull --platform" in docker.verbs()
        assert "docker load --quiet" in docker.verbs()

    def test_bench_should_skip_the_split_when_crane_is_not_installed(
        self, docker: FakeDocker, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(bench, "have_crane", lambda: False)

        rows = bench.bench(IMAGE, 1, "p/baseline", "r", "cold", tmp_path / "out.jsonl", split=True)

        assert rows[0]["download_s"] is None
        assert rows[0]["compressed_bytes"] is None
        assert not any(v.startswith("crane") for v in docker.verbs())

    def test_bench_should_keep_going_when_the_split_download_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        fake = FakeDocker(fail=("crane pull",))
        monkeypatch.setattr(bench, "run", fake)
        monkeypatch.setattr(bench, "have_crane", lambda: True)

        rows = bench.bench(IMAGE, 1, "p/baseline", "r", "cold", tmp_path / "out.jsonl", split=True)

        assert rows[0]["download_s"] is not None

    def test_compressed_bytes_should_be_none_when_the_manifest_is_not_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(bench, "run", FakeDocker(manifest="not json"))
        monkeypatch.setattr(bench, "have_crane", lambda: True)

        assert bench.compressed_bytes(IMAGE) is None

    def test_bench_should_raise_when_the_pull_fails(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(bench, "run", FakeDocker(fail=("docker pull",)))
        monkeypatch.setattr(bench, "have_crane", lambda: False)

        with pytest.raises(bench.BenchError):
            bench.bench(IMAGE, 1, "p/baseline", "r", "cold", tmp_path / "out.jsonl", split=False)


class TestMain:
    def test_main_should_default_to_five_runs_when_the_runs_argument_is_left_out(
        self, docker: FakeDocker, tmp_path: Path
    ) -> None:
        out = tmp_path / "out.jsonl"

        code = bench.main([IMAGE, "p/baseline", "github-hosted", "--out", str(out)])

        assert code == 0
        assert len(out.read_text().splitlines()) == 5

    def test_main_should_use_the_environment_when_no_options_are_given(
        self, docker: FakeDocker, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        out = tmp_path / "env.jsonl"
        monkeypatch.setenv("BENCH_OUT", str(out))
        monkeypatch.setenv("BENCH_MODE", "warm")

        code = bench.main([IMAGE, "2", "p/baseline", "r"])

        assert code == 0
        assert [json.loads(line)["mode"] for line in out.read_text().splitlines()] == ["warm", "warm"]

    def test_main_should_return_one_when_a_docker_call_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(bench, "run", FakeDocker(fail=("docker pull",)))
        monkeypatch.setattr(bench, "have_crane", lambda: False)

        code = bench.main([IMAGE, "1", "p/baseline", "r", "--out", str(tmp_path / "o.jsonl")])

        assert code == 1
        assert "docker pull" in capsys.readouterr().out

    def test_main_should_return_two_when_variant_and_runner_are_missing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = bench.main([IMAGE, "3", "only-a-variant"])

        assert code == 2
        assert "usage: superlint-lean bench" in capsys.readouterr().out

    def test_cli_should_list_bench_when_usage_is_printed(self, capsys: pytest.CaptureFixture[str]) -> None:
        cli.main([])

        assert "bench" in capsys.readouterr().out


class TestRun:
    def test_run_should_return_the_output_when_the_command_succeeds(self) -> None:
        completed = bench.run([sys.executable, "-c", "print('ok')"])

        assert completed.stdout.strip() == "ok"

    def test_run_should_raise_with_the_error_text_when_a_checked_command_fails(self) -> None:
        with pytest.raises(bench.BenchError, match="boom"):
            bench.run([sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])

    def test_run_should_return_the_failure_when_the_check_is_off(self) -> None:
        completed = bench.run([sys.executable, "-c", "import sys; sys.exit(3)"], check=False)

        assert completed.returncode == 3

    def test_timed_should_return_the_elapsed_seconds_rounded_to_two_decimals(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ticks = iter([10.0, 10.1234])
        monkeypatch.setattr(bench.time, "perf_counter", lambda: next(ticks))

        assert bench.timed(lambda: None) == 0.12
