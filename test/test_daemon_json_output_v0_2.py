"""The daemon's stdout is a JSON protocol, including on a fresh database."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DAEMON = ROOT / "tools/daemon/memory_observer_daemon_v0_2.py"


class DaemonJsonOutputTest(unittest.TestCase):
    def test_startup_diagnostics_do_not_contaminate_json_stdout(self):
        with tempfile.TemporaryDirectory(prefix="mk-daemon-json-") as td:
            work = Path(td)
            events = work / "events.jsonl"
            events.write_text("", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(DAEMON), "--run-once",
                    "--events-file", str(events),
                    "--state-db", str(work / "state.sqlite"),
                    "--pid-file", str(work / "daemon.pid"),
                    "--lock-file", str(work / "daemon.lock"),
                ],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertTrue(output["ok"])
            self.assertEqual(output["processed_this_run"], 0)
            self.assertIn("[heal]", result.stderr)


if __name__ == "__main__":
    unittest.main()
