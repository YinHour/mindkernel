from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ValidateMemoryImportV01Test(unittest.TestCase):
    def test_validate_memory_import_script(self):
        root = Path(__file__).resolve().parents[1]
        cmd = ["python3", "tools/validate_memory_import_v0_1.py"]
        p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, msg=f"stderr: {p.stderr}\nstdout: {p.stdout}")

        out = json.loads(p.stdout)
        self.assertTrue(out.get("ok"))
        self.assertGreaterEqual(int(out.get("rows", 0)), 3)
        self.assertEqual(int(out.get("run2", {}).get("failed", 1)), 0)
        self.assertGreaterEqual(int(out.get("run3", {}).get("failed", 0)), 1)


if __name__ == "__main__":
    unittest.main()
