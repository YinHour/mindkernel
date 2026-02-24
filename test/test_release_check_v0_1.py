from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ReleaseCheckV01Test(unittest.TestCase):
    def test_release_check_quick_mode(self):
        root = Path(__file__).resolve().parents[1]
        cmd = [
            "python3",
            "tools/release_check_v0_1.py",
            "--quick",
            "--no-strict",
            "--out-json",
            "reports/release_check_quick_test.json",
            "--out-md",
            "reports/release_check_quick_test.md",
        ]
        p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, msg=f"stderr: {p.stderr}\nstdout: {p.stdout}")

        out = json.loads(p.stdout)
        self.assertIn("passed", out)
        self.assertIn("total", out)
        self.assertGreaterEqual(int(out.get("total", 0)), 1)


if __name__ == "__main__":
    unittest.main()
