import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import qnt30702_operator_command_console_router as c
from backend.app import qnt30703_live_broker_safety_layer_router as s
from backend.app import qnt30700_institutional_release_control_router as r


class OperatorConsoleSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="qnt30702_")
        self.email = "operator@example.com"
        self.console_dir = Path(self.tempdir) / "console"
        self.safety_dir = Path(self.tempdir) / "safety"
        self.release_dir = Path(self.tempdir) / "release"
        self.console_dir.mkdir(parents=True, exist_ok=True)
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.release_dir.mkdir(parents=True, exist_ok=True)
        self.patches = [
            patch.object(c, "CONSOLE_DIR", self.console_dir),
            patch.object(c, "_require_user", lambda: {"email": self.email}),
            patch.object(s, "LAYER_DIR", self.safety_dir),
            patch.object(s, "_require_user", lambda: {"email": self.email}),
            patch.object(r, "RELEASE_DIR", self.release_dir),
            patch.object(r, "SAFETY_DIR", self.safety_dir),
            patch.object(r, "_require_user", lambda: {"email": self.email}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_console_lifecycle(self):
        boot = c.operator_command_console_bootstrap_demo({"email": self.email})
        self.assertEqual(boot["status"], "bootstrapped")
        s.live_broker_safety_layer_run({"trigger": "smoke"})

        pause = c.operator_command_console_command({"action": "pause_execution", "reason": "desk review"})
        self.assertTrue(pause["summary"]["operator_console_status"]["execution_paused"])

        require = c.operator_command_console_command({"action": "require_operator_override", "reason": "manual desk mode"})
        self.assertTrue(require["summary"]["safety"]["controls"]["operator_override_required"])

        release = r.institutional_release_control_propose({
            "version": "v3.07.02",
            "title": "operator seat live",
            "changes": ["console router", "console ui"],
            "affected_modules": ["backend/app/main.py"],
            "rationale": "add operator command console",
        })["release"]

        approved = c.operator_command_console_command({"action": "approve_release", "release_id": release["release_id"], "reason": "operator signoff"})
        self.assertTrue(approved["command"]["details"]["release"]["approved"])

        c.operator_command_console_command({"action": "resume_execution", "reason": "review complete"})
        deployed = c.operator_command_console_command({"action": "deploy_release", "release_id": release["release_id"], "reason": "deploy now"})
        self.assertTrue(deployed["command"]["details"]["release"]["deployed"])

        stopped = c.operator_command_console_command({"action": "emergency_stop", "reason": "containment test"})
        self.assertTrue(stopped["summary"]["operator_console_status"]["kill_switch"])


if __name__ == "__main__":
    unittest.main()
