from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ValidateRecallQualityV01Test(unittest.TestCase):
    def test_validate_recall_quality_script(self):
        root = Path(__file__).resolve().parents[1]
        cmd = [
            "python3",
            "tools/validate_recall_quality_v0_1.py",
            "--no-strict",
        ]
        p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, msg=f"stderr: {p.stderr}\nstdout: {p.stdout}")

        out = json.loads(p.stdout)
        self.assertTrue(out.get("ok"))
        metrics = out.get("metrics", {})
        self.assertGreaterEqual(float(metrics.get("accuracy", 0.0)), 0.8)
        self.assertGreaterEqual(float(metrics.get("macro_recall", 0.0)), 0.8)
        self.assertLessEqual(float(metrics.get("macro_noise", 1.0)), 0.75)


if __name__ == "__main__":
    unittest.main()
