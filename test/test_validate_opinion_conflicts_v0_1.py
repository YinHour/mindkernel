from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ValidateOpinionConflictsV01Test(unittest.TestCase):
    def test_validate_opinion_conflicts_script(self):
        root = Path(__file__).resolve().parents[1]
        cmd = ["python3", "tools/validate_opinion_conflicts_v0_1.py"]
        p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, msg=f"stderr: {p.stderr}\nstdout: {p.stdout}")

        out = json.loads(p.stdout)
        self.assertTrue(out.get("ok"))
        self.assertGreaterEqual(int(out.get("conflict_groups", 0)), 1)
        top = out.get("top_group", {})
        self.assertEqual(top.get("recommended_action"), "mandatory_review")


if __name__ == "__main__":
    unittest.main()
