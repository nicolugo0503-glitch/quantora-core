import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import qnt30705_fund_admin_control_center_router as facc
from backend.app import qnt30624_capital_ledger_router as ledger
from backend.app import qnt30625_waterfall_router as waterfall
from backend.app import qnt30627_statement_batch_router as statements
from backend.app import qnt30628_performance_engine_router as perf
from backend.app import qnt30636_operations_fund_admin_router as ops
from backend.app import qnt30703_live_broker_safety_layer_router as safety
from backend.app import qnt30700_institutional_release_control_router as release
from backend.app import qnt30702_operator_command_console_router as console
from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
from backend.app import qnt30588_statement_pack_router as pack
from backend.app import qnt30589_report_delivery_log_router as log
from backend.app import qnt30590_reporting_calendar_router as cal


class FundAdminControlCenterSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="qnt30705_")
        self.email = "operator@example.com"
        self.dirs = {}
        for name in ["facc", "ledger", "waterfall", "statements", "perf", "ops", "safety", "release", "console", "delivery", "pack", "log", "cal"]:
            p = Path(self.tempdir) / name
            p.mkdir(parents=True, exist_ok=True)
            self.dirs[name] = p
        self.patches = [
            patch.object(facc, "ADMIN_DIR", self.dirs["facc"]),
            patch.object(facc, "_require_user", lambda: {"email": self.email}),
            patch.object(ledger, "LEDGER_DIR", self.dirs["ledger"]),
            patch.object(waterfall, "WATERFALL_DIR", self.dirs["waterfall"]),
            patch.object(statements, "STATEMENT_DIR", self.dirs["statements"]),
            patch.object(perf, "PERF_DIR", self.dirs["perf"]),
            patch.object(ops, "OPS_DIR", self.dirs["ops"]),
            patch.object(safety, "LAYER_DIR", self.dirs["safety"]),
            patch.object(release, "RELEASE_DIR", self.dirs["release"]),
            patch.object(release, "SAFETY_DIR", self.dirs["safety"]),
            patch.object(console, "CONSOLE_DIR", self.dirs["console"]),
            patch.object(delivery, "DELIVERY_DIR", self.dirs["delivery"]),
            patch.object(pack, "PACK_DIR", self.dirs["pack"]),
            patch.object(log, "LOG_DIR", self.dirs["log"]),
            patch.object(cal, "CAL_DIR", self.dirs["cal"]),
            patch.object(statements, "_require_user", lambda: {"email": self.email}),
            patch.object(ops, "_require_user", lambda: {"email": self.email}),
            patch.object(safety, "_require_user", lambda: {"email": self.email}),
            patch.object(release, "_require_user", lambda: {"email": self.email}),
            patch.object(console, "_require_user", lambda: {"email": self.email}),
            patch.object(delivery, "_require_user", lambda: {"email": self.email}),
            patch.object(pack, "_require_user", lambda: {"email": self.email}),
            patch.object(log, "_require_user", lambda: {"email": self.email}),
            patch.object(cal, "_require_user", lambda: {"email": self.email}),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_fund_admin_lifecycle(self):
        boot = facc.fund_admin_control_center_bootstrap_demo({"email": self.email})
        self.assertEqual(boot["status"], "bootstrapped")
        summary = boot["summary"]
        self.assertEqual(summary["mission"], "QNT30705")
        self.assertGreaterEqual(summary["capital_summary"]["investor_count"], 2)
        self.assertGreater(summary["aum"], 0)

        flow = facc.fund_admin_control_center_record_flow({"type": "distribution", "amount": 25000, "notes": "quarter-end distribution"})
        self.assertEqual(flow["status"], "recorded")
        self.assertEqual(flow["flow"]["type"], "distribution")

        close = facc.fund_admin_control_center_run_close({"notes": "month end close"})
        self.assertEqual(close["status"], "closed")
        self.assertEqual(close["close_run"]["status"], "closed")
        self.assertGreaterEqual(len(close["summary"]["close_runs"]), 1)


if __name__ == "__main__":
    unittest.main()
