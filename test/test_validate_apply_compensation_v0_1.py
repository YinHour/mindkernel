from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ValidateApplyCompensationV01Test(unittest.TestCase):
    def test_validate_apply_compensation_script(self):
        root = Path(__file__).resolve().parents[1]
        cmd = ["python3", "tools/validate_apply_compensation_v0_1.py"]
        p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, msg=f"stderr: {p.stderr}\nstdout: {p.stdout}")

        out = json.loads(p.stdout)
        self.assertTrue(out.get("ok"))
        self.assertGreaterEqual(int(out.get("apply", {}).get("compensation_created", 0)), 1)
        self.assertEqual(out.get("compensation", {}).get("status"), "resolved")


if __name__ == "__main__":
    unittest.main()
