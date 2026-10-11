import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rows(path, items):
    Path(path).write_text("\n".join(json.dumps(i) for i in items) + "\n")


def bench(kind, pull, unpacked=1048576 * 700, comp=1048576 * 150, mode="cold"):
    return {"variant": f"p/{kind}", "mode": mode, "pull_s": pull, "uncompressed_bytes": unpacked,
            "compressed_bytes": comp}


class ReleaseNotes(unittest.TestCase):
    def run_notes(self, old, new, profiles="p"):
        with tempfile.TemporaryDirectory() as d:
            for name, items in (("old", old), ("new", new)):
                Path(d, name).mkdir()
                rows(Path(d, name, "bench-p.jsonl"), items)
            out = subprocess.run([sys.executable, str(ROOT / "scripts/release_notes.py"), "--old-tag", "v1",
                                  "--old-dir", f"{d}/old", "--new-tag", "v2", "--new-dir", f"{d}/new",
                                  "--profiles", profiles], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_before_and_after(self):
        old = [bench("lean-gzip", 10.0), bench("lean-zstd", 5.0), bench("baseline", 70.0, 5000 * 1048576)]
        new = [bench("lean-gzip", 9.0), bench("lean-zstd", 5.0), bench("baseline", 72.0, 5200 * 1048576)]
        text = self.run_notes(old, new)
        self.assertIn("| p | 10.0 s | 9.0 s | -10% |", text)
        self.assertIn("| p | 70.0 s | 72.0 s | +3% | 5000 MB | 5200 MB | +4% |", text)

    def test_profile_missing_in_old_is_reported(self):
        text = self.run_notes([], [bench("lean-gzip", 9.0)])
        self.assertIn("nothing to compare", text)

    def test_medians(self):
        old = [bench("lean-gzip", x) for x in (10.0, 30.0, 11.0)]
        new = [bench("lean-gzip", 11.0)]
        self.assertIn("| p | 11.0 s | 11.0 s | +0% |", self.run_notes(old, new))


if __name__ == "__main__":
    unittest.main()
