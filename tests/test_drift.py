import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "compiler"))
import drift_check  # noqa: E402
import slconfig  # noqa: E402

UPSTREAM = set(json.loads((ROOT / "compiler/linters.json").read_text())["linters"])
TABLE = json.loads((ROOT / "compiler/filetypes.json").read_text())
FIXTURE = ROOT / "tests/fixtures/ghwm-workflow.yml"


def run(env, files, **kw):
    return {f["file"]: f["flags"] for f in drift_check.check(env, files, UPSTREAM, TABLE, **kw)}


class Semantics(unittest.TestCase):
    def test_nothing_set_enables_everything(self):
        self.assertEqual(set(slconfig.effective_flags({}, UPSTREAM)), UPSTREAM)

    def test_true_flags_only(self):
        self.assertEqual(slconfig.effective_flags({"VALIDATE_YAML": "true", "VALIDATE_JSON": "true"}, UPSTREAM),
                         ["JSON", "YAML"])

    def test_false_flags_remove(self):
        got = set(slconfig.effective_flags({"VALIDATE_YAML": "false"}, UPSTREAM))
        self.assertEqual(got, UPSTREAM - {"YAML"})

    def test_mixing_is_an_error(self):
        with self.assertRaises(slconfig.ConfigError):
            slconfig.effective_flags({"VALIDATE_YAML": "true", "VALIDATE_JSON": "false"}, UPSTREAM)

    def test_all_codebase_is_not_a_linter(self):
        self.assertEqual(slconfig.effective_flags({"VALIDATE_ALL_CODEBASE": "true", "VALIDATE_YAML": "true"}, UPSTREAM),
                         ["YAML"])

    def test_invalid_value(self):
        with self.assertRaises(slconfig.ConfigError):
            slconfig.effective_flags({"VALIDATE_YAML": "yes"}, UPSTREAM)


class Ghwm(unittest.TestCase):
    def setUp(self):
        self.env = slconfig.parse_workflow(FIXTURE)

    def test_workflow_discovery(self):
        self.assertEqual(self.env["VALIDATE_PYTHON_RUFF"], "true")
        self.assertEqual(self.env["LINTER_RULES_PATH"], ".github/linters")
        self.assertEqual(len(slconfig.effective_flags(self.env, UPSTREAM)), 12)

    def test_covered_files(self):
        files = ["src/a.py", "README.md", "package.json", ".github/workflows/x.yml", "conf.yaml", "notes.txt"]
        self.assertEqual(run(self.env, files), {})

    def test_new_languages_are_flagged(self):
        got = run(self.env, ["src/main.rs", "web/app.ts", "Dockerfile", "ci/build.sh"])
        self.assertEqual(set(got), {"src/main.rs", "web/app.ts", "Dockerfile", "ci/build.sh"})
        self.assertIn("RUST_2024", got["src/main.rs"])
        self.assertIn("DOCKERFILE_HADOLINT", got["Dockerfile"])

    def test_exclude_regex_is_respected(self):
        self.assertEqual(run(self.env, [".agents/tool.rs", "x/skills-lock.json.rs"]), {})

    def test_allow_extension(self):
        self.assertEqual(run(self.env, ["a.rs"], allow_ext=("rs",)), {})

    def test_allow_file_name(self):
        self.assertEqual(run(self.env, ["ci/Dockerfile"], allow_ext=("dockerfile",)), {})

    def test_include_regex(self):
        env = {**self.env, "FILTER_REGEX_INCLUDE": ".*src/.*"}
        self.assertEqual(set(run(env, ["src/a.rs", "other/b.rs"])), {"src/a.rs"})

    def test_shebang_script_without_extension(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "bin").mkdir()
            Path(d, "bin/run").write_text("#!/usr/bin/env bash\necho hi\n")
            Path(d, "bin/tool").write_text("#!/usr/bin/env python3\nprint(1)\n")
            got = run(self.env, ["bin/run", "bin/tool"], root=d)
        self.assertEqual(set(got), {"bin/run"})  # python is covered, shell is not

    def test_dependabot_needs_zizmor(self):
        env = {"VALIDATE_YAML": "true"}
        self.assertEqual(run(env, [".github/dependabot.yml"]), {})  # YAML covers it
        env = {"VALIDATE_JSON": "true"}
        self.assertIn(".github/dependabot.yml", run(env, [".github/dependabot.yml"]))


class Table(unittest.TestCase):
    def test_every_flag_in_table_is_mapped(self):
        used = {f for r in TABLE["rules"] for f in r["flags"]}
        self.assertEqual(used - UPSTREAM, set())

    def test_always_on_flags_are_mapped(self):
        self.assertEqual(set(TABLE["always_on"]) - UPSTREAM, set())


if __name__ == "__main__":
    unittest.main()
