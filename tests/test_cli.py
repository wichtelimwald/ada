from __future__ import annotations

import json
import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def test_doctor(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ada", "doctor"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("python", payload)


if __name__ == "__main__":
    unittest.main()
