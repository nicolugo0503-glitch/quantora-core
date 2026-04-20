import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import qnt30700_institutional_release_control_router as r


class ReleaseControlSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="qnt30700_")
        self.email = "operator@example.com"
        self.release_dir = Path(self.tempdir) / "release"
        self.safety_dir = Path(self.tempdir) / "safety"
        self.release_dir.mkdir(parents=True, exist_ok=True)
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.patches = [
            patch.object(r, "RELEASE_DIR", self.release_dir),
            patch.object(r, "SAFETY_DIR", self.safety_dir),
            patch.object(r, "_require_user", lambda: {"email": self.email}),
        ]
        for p in self.patches:
            p.start()
        safety = {
            "runs": [{
                "posture": "SAFE",
                "production_ready": True,
                "risk_score": 91.0,
                "daily_drawdown_pct": 0.01,
                "open_exposure_pct": 0.22,
                "kill_switch": False,
                "execution_paused": False,
            }],
            "trade_checks": []
        }
        self.safety_file = self.safety_dir / f"{r._safe(self.email)}.json"
        self.safety_file.write_text(json.dumps(safety), encoding="utf-8")

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_release_lifecycle(self):
        boot = r.institutional_release_control_bootstrap_demo({"email": self.email})
        self.assertEqual(boot["status"], "bootstrapped")
        proposal = r.institutional_release_control_propose({
            "version": "v3.07.00",
            "title": "release control live",
            "changes": ["router added", "ui added"],
            "affected_modules": ["backend/app/main.py"],
            "rationale": "govern production changes",
        })
        rel = proposal["release"]
        self.assertTrue(rel["validation"]["simulation_passed"])
        approved = r.institutional_release_control_approve({"release_id": rel["release_id"]})
        self.assertTrue(approved["release"]["approved"])
        deployed = r.institutional_release_control_deploy({"release_id": rel["release_id"]})
        self.assertTrue(deployed["release"]["deployed"])
        self.assertEqual(deployed["summary"]["active_version"], "v3.07.00")
        rolled = r.institutional_release_control_rollback({"reason": "test rollback"})
        self.assertEqual(rolled["status"], "rolled_back")
        self.assertEqual(rolled["summary"]["active_version"], "v3.07.03")


if __name__ == "__main__":
    unittest.main()
