"""Tests for superlint_lean.generate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from superlint_lean import generate
from tests.shared import PYTHON_BASE, UPSTREAM_TAG, WORKFLOW_FIXTURE


def run_generate(out: Path, upstream_dockerfile: Path, *args: str) -> dict[str, Any]:
    code = generate.main(
        ["--upstream-tag", UPSTREAM_TAG, "--upstream-dockerfile", str(upstream_dockerfile), "--out", str(out), *args]
    )
    assert code == 0
    plan: dict[str, Any] = json.loads((out / "plan.json").read_text())
    return plan


@pytest.fixture
def yaml_env(tmp_path: Path) -> Path:
    path = tmp_path / "yaml.env"
    path.write_text("VALIDATE_YAML=true\nVALIDATE_ALL_CODEBASE=true\n")
    return path


class TestGenerateOutputs:
    def test_generate_should_write_the_build_context_when_one_env_file_is_given(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        out = tmp_path / "out"

        run_generate(out, upstream_dockerfile, "--env", str(yaml_env))

        assert {path.name for path in out.iterdir()} == {
            "Dockerfile",
            "checks.sh",
            "plan.json",
            "prune-node-modules.js",
        }

    def test_generate_should_pin_the_upstream_image_when_a_tag_is_given(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        out = tmp_path / "out"

        plan = run_generate(out, upstream_dockerfile, "--env", str(yaml_env))

        assert plan["upstream_image"] == f"ghcr.io/super-linter/super-linter:slim-{UPSTREAM_TAG}"
        assert plan["baseline_variant"] == "slim"
        assert f"FROM {PYTHON_BASE}" in (out / "Dockerfile").read_text()

    def test_generate_should_set_the_build_variables_when_the_image_is_generated(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        out = tmp_path / "out"

        run_generate(out, upstream_dockerfile, "--env", str(yaml_env))

        dockerfile = (out / "Dockerfile").read_text()
        assert "ARG BUILD_VERSION=9.0.0" in dockerfile
        assert "ENV BUILD_VERSION=$BUILD_VERSION BUILD_REVISION=$BUILD_REVISION BUILD_DATE=$BUILD_DATE" in dockerfile

    def test_generate_should_ignore_all_codebase_when_it_is_set_in_the_env_file(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        plan = run_generate(tmp_path / "out", upstream_dockerfile, "--env", str(yaml_env))

        assert plan["flags"] == ["YAML"]

    def test_generate_should_test_symlinks_with_a_valid_operator_when_copying_upstream_paths(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        out = tmp_path / "out"

        run_generate(out, upstream_dockerfile, "--env", str(yaml_env))

        assert '[ -L "$p" ]' in (out / "Dockerfile").read_text()

    def test_generate_should_use_the_standard_image_when_a_linter_needs_it(
        self, tmp_path: Path, upstream_dockerfile: Path
    ) -> None:
        env = tmp_path / "arm.env"
        env.write_text("VALIDATE_ARM=true\n")

        plan = run_generate(tmp_path / "out", upstream_dockerfile, "--env", str(env))

        assert plan["upstream_image"] == f"ghcr.io/super-linter/super-linter:{UPSTREAM_TAG}"
        assert plan["baseline_variant"] == "standard"

    def test_generate_should_write_one_check_per_tool_when_linters_define_checks(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        out = tmp_path / "out"

        run_generate(out, upstream_dockerfile, "--env", str(yaml_env))

        assert "run_check 'yamllint -c" in (out / "checks.sh").read_text()


class TestGenerateSelection:
    def test_generate_should_stack_flags_when_several_env_files_are_given(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        json_env = tmp_path / "json.env"
        json_env.write_text("VALIDATE_JSON=true\nVALIDATE_YAML=true\n")

        plan = run_generate(tmp_path / "out", upstream_dockerfile, "--env", str(yaml_env), "--env", str(json_env))

        assert plan["flags"] == ["YAML", "JSON"]

    def test_generate_should_drop_flags_when_exclude_is_given(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        json_env = tmp_path / "json.env"
        json_env.write_text("VALIDATE_JSON=true\n")

        plan = run_generate(
            tmp_path / "out",
            upstream_dockerfile,
            "--env",
            str(yaml_env),
            "--env",
            str(json_env),
            "--exclude",
            "VALIDATE_JSON",
        )

        assert plan["flags"] == ["YAML"]

    def test_generate_should_read_flags_from_the_workflow_when_workflow_is_given(
        self, tmp_path: Path, upstream_dockerfile: Path
    ) -> None:
        plan = run_generate(tmp_path / "out", upstream_dockerfile, "--workflow", str(WORKFLOW_FIXTURE))

        assert len(plan["flags"]) == 12
        assert "PYTHON_RUFF" in plan["flags"]

    def test_generate_should_select_every_mapped_flag_when_all_is_given(
        self, tmp_path: Path, upstream_dockerfile: Path, upstream_flags: set[str]
    ) -> None:
        plan = run_generate(tmp_path / "out", upstream_dockerfile, "--all")

        assert set(plan["flags"]) == upstream_flags - {"ALL_CODEBASE"}

    def test_generate_should_exit_when_nothing_is_selected(self, tmp_path: Path, upstream_dockerfile: Path) -> None:
        with pytest.raises(SystemExit, match="give at least one"):
            generate.main(
                [
                    "--upstream-tag",
                    UPSTREAM_TAG,
                    "--upstream-dockerfile",
                    str(upstream_dockerfile),
                    "--out",
                    str(tmp_path / "out"),
                ]
            )

    def test_generate_should_exit_when_a_flag_has_no_mapping(self, tmp_path: Path, upstream_dockerfile: Path) -> None:
        env = tmp_path / "bad.env"
        env.write_text("VALIDATE_NOT_A_LINTER=true\n")

        with pytest.raises(SystemExit, match="no mapping for: NOT_A_LINTER"):
            generate.main(
                [
                    "--upstream-tag",
                    UPSTREAM_TAG,
                    "--upstream-dockerfile",
                    str(upstream_dockerfile),
                    "--out",
                    str(tmp_path / "out"),
                    "--env",
                    str(env),
                ]
            )

    def test_generate_should_exit_when_the_workflow_has_no_super_linter_step(
        self, tmp_path: Path, upstream_dockerfile: Path
    ) -> None:
        workflow = tmp_path / "w.yml"
        workflow.write_text("jobs:\n  a:\n    steps:\n      - run: echo\n")

        with pytest.raises(SystemExit, match="no super-linter"):
            generate.main(
                [
                    "--upstream-tag",
                    UPSTREAM_TAG,
                    "--upstream-dockerfile",
                    str(upstream_dockerfile),
                    "--out",
                    str(tmp_path / "out"),
                    "--workflow",
                    str(workflow),
                ]
            )

    def test_generate_should_exit_when_upstream_dockerfile_has_no_python_base(
        self, tmp_path: Path, yaml_env: Path
    ) -> None:
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM alpine\n")

        with pytest.raises(SystemExit, match="python-base"):
            generate.main(
                [
                    "--upstream-tag",
                    UPSTREAM_TAG,
                    "--upstream-dockerfile",
                    str(dockerfile),
                    "--out",
                    str(tmp_path / "out"),
                    "--env",
                    str(yaml_env),
                ]
            )


class TestGenerateExtras:
    def test_generate_should_install_extras_in_their_own_layers_when_extra_flags_are_given(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        out = tmp_path / "out"

        plan = run_generate(
            out,
            upstream_dockerfile,
            "--env",
            str(yaml_env),
            "--extra-apk",
            "tree",
            "--extra-npm",
            "left-pad@1.3.0",
            "--extra-pip",
            "yq==3.4.3",
            "--extra-check",
            "tree --version",
        )

        dockerfile = (out / "Dockerfile").read_text()
        assert plan["extras"] == {
            "apk": ["tree"],
            "npm": ["left-pad@1.3.0"],
            "pip": ["yq==3.4.3"],
            "check": ["tree --version"],
        }
        assert "AS extra-npm" in dockerfile
        assert "--ignore-scripts" in dockerfile
        assert "AS extra-pip" in dockerfile

    def test_generate_should_read_extras_from_the_env_file_when_extra_variables_are_set(
        self, tmp_path: Path, upstream_dockerfile: Path, yaml_env: Path
    ) -> None:
        extras_env = tmp_path / "extras.env"
        extras_env.write_text('EXTRA_APK="tree jq"\nEXTRA_CHECK="tree --version"\nEXTRA_CHECK="jq --version"\n')

        plan = run_generate(tmp_path / "out", upstream_dockerfile, "--env", str(yaml_env), "--env", str(extras_env))

        assert plan["extras"]["apk"] == ["tree", "jq"]
        assert plan["extras"]["check"] == ["tree --version", "jq --version"]

    def test_generate_should_include_node_pruning_when_a_linter_needs_npm_packages(
        self, tmp_path: Path, upstream_dockerfile: Path
    ) -> None:
        env = tmp_path / "md.env"
        env.write_text("VALIDATE_MARKDOWN=true\n")
        out = tmp_path / "out"

        plan = run_generate(out, upstream_dockerfile, "--env", str(env))

        assert plan["npm_roots"]
        assert "AS npm-prune" in (out / "Dockerfile").read_text()
