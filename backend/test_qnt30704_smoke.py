import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import qnt30704_investor_delivery_pack_system_router as d
from backend.app import qnt30703_live_broker_safety_layer_router as s
from backend.app import qnt30700_institutional_release_control_router as r
from backend.app import qnt30702_operator_command_console_router as c
from backend.app import qnt30588_statement_pack_router as p
from backend.app import qnt30589_report_delivery_log_router as l
from backend.app import qnt30590_reporting_calendar_router as cal


class InvestorDeliveryPackSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="qnt30704_")
        self.email = "operator@example.com"
        self.delivery_dir = Path(self.tempdir) / "delivery"
        self.safety_dir = Path(self.tempdir) / "safety"
        self.release_dir = Path(self.tempdir) / "release"
        self.console_dir = Path(self.tempdir) / "console"
        self.statement_dir = Path(self.tempdir) / "statement"
        self.log_dir = Path(self.tempdir) / "log"
        self.calendar_dir = Path(self.tempdir) / "calendar"
        for path in [self.delivery_dir, self.safety_dir, self.release_dir, self.console_dir, self.statement_dir, self.log_dir, self.calendar_dir]:
            path.mkdir(parents=True, exist_ok=True)
        self.patches = [
            patch.object(d, "DELIVERY_DIR", self.delivery_dir),
            patch.object(d, "_require_user", lambda: {"email": self.email}),
            patch.object(s, "LAYER_DIR", self.safety_dir),
            patch.object(r, "RELEASE_DIR", self.release_dir),
            patch.object(r, "SAFETY_DIR", self.safety_dir),
            patch.object(c, "CONSOLE_DIR", self.console_dir),
            patch.object(p, "PACK_DIR", self.statement_dir),
            patch.object(l, "LOG_DIR", self.log_dir),
            patch.object(cal, "CAL_DIR", self.calendar_dir),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_delivery_pack_lifecycle(self):
        boot = d.investor_delivery_pack_system_bootstrap_demo({"email": self.email})
        self.assertEqual(boot["status"], "bootstrapped")
        summary = boot["summary"]
        self.assertEqual(summary["mission"], "QNT30704")
        self.assertGreaterEqual(summary["recipient_count"], 2)

        built = d.investor_delivery_pack_system_build({
            "title": "Quarterly Investor Delivery Pack",
            "operator_note": "Quarter-end institutional distribution.",
        })
        self.assertEqual(built["status"], "generated")
        pack_id = built["pack"]["pack_id"]

        delivered = d.investor_delivery_pack_system_deliver({
            "pack_id": pack_id,
            "channel": "secure_email_simulated",
            "notes": "Distribute to active LP list",
        })
        self.assertEqual(delivered["status"], "delivered")
        self.assertEqual(delivered["pack"]["delivery_status"], "delivered")
        self.assertEqual(delivered["delivery_event"]["ack_status"], "pending")

        configured = d.investor_delivery_pack_system_template({
            "template_id": "tmpl_quarterly_board",
            "name": "quarterly board pack",
            "sections": ["cover_letter", "performance_summary", "board_notes"],
            "policy": {"default_channel": "secure_email_simulated"},
        })
        self.assertEqual(configured["status"], "configured")
        self.assertGreaterEqual(configured["summary"]["template_count"], 2)


if __name__ == "__main__":
    unittest.main()
