import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import qnt30708_strategy_evolution_engine_router as engine
from backend.app import qnt30707_recovery_system_router as recovery
from backend.app import qnt30706_forensic_audit_system_router as forensic
from backend.app import qnt30602_audit_trail_router as audit
from backend.app import qnt30700_institutional_release_control_router as release
from backend.app import qnt30702_operator_command_console_router as console
from backend.app import qnt30703_live_broker_safety_layer_router as safety
from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
from backend.app import qnt30624_capital_ledger_router as ledger
from backend.app import qnt30625_waterfall_router as waterfall
from backend.app import qnt30627_statement_batch_router as statements
from backend.app import qnt30628_performance_engine_router as perf
from backend.app import qnt30636_operations_fund_admin_router as ops
from backend.app import qnt30588_statement_pack_router as pack
from backend.app import qnt30589_report_delivery_log_router as log
from backend.app import qnt30590_reporting_calendar_router as cal


class StrategyEvolutionEngineSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="qnt30708_")
        self.email = "operator@example.com"
        names = ["engine", "recovery", "forensic", "audit", "release", "console", "safety", "delivery", "fund_admin", "ledger", "waterfall", "statements", "perf", "ops", "pack", "log", "cal"]
        self.dirs = {}
        for name in names:
            p = Path(self.tempdir) / name
            p.mkdir(parents=True, exist_ok=True)
            self.dirs[name] = p
        self.patches = [
            patch.object(engine, "ENGINE_DIR", self.dirs["engine"]),
            patch.object(engine, "_require_user", lambda: {"email": self.email}),
            patch.object(recovery, "RECOVERY_DIR", self.dirs["recovery"]),
            patch.object(recovery, "_require_user", lambda: {"email": self.email}),
            patch.object(forensic, "FORENSIC_DIR", self.dirs["forensic"]),
            patch.object(forensic, "_require_user", lambda: {"email": self.email}),
            patch.object(audit, "AUDIT_DIR", self.dirs["audit"]),
            patch.object(audit, "_require_user", lambda: {"email": self.email}),
            patch.object(release, "RELEASE_DIR", self.dirs["release"]),
            patch.object(release, "SAFETY_DIR", self.dirs["safety"]),
            patch.object(release, "_require_user", lambda: {"email": self.email}),
            patch.object(console, "CONSOLE_DIR", self.dirs["console"]),
            patch.object(console, "_require_user", lambda: {"email": self.email}),
            patch.object(safety, "LAYER_DIR", self.dirs["safety"]),
            patch.object(safety, "_require_user", lambda: {"email": self.email}),
            patch.object(delivery, "DELIVERY_DIR", self.dirs["delivery"]),
            patch.object(delivery, "_require_user", lambda: {"email": self.email}),
            patch.object(fund_admin, "ADMIN_DIR", self.dirs["fund_admin"]),
            patch.object(fund_admin, "_require_user", lambda: {"email": self.email}),
            patch.object(ledger, "LEDGER_DIR", self.dirs["ledger"]),
            patch.object(waterfall, "WATERFALL_DIR", self.dirs["waterfall"]),
            patch.object(statements, "STATEMENT_DIR", self.dirs["statements"]),
            patch.object(perf, "PERF_DIR", self.dirs["perf"]),
            patch.object(ops, "OPS_DIR", self.dirs["ops"]),
            patch.object(pack, "PACK_DIR", self.dirs["pack"]),
            patch.object(log, "LOG_DIR", self.dirs["log"]),
            patch.object(cal, "CAL_DIR", self.dirs["cal"]),
            patch.object(statements, "_require_user", lambda: {"email": self.email}),
            patch.object(ops, "_require_user", lambda: {"email": self.email}),
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

    def test_strategy_evolution_lifecycle(self):
        boot = engine.strategy_evolution_engine_bootstrap_demo({"email": self.email})
        self.assertEqual(boot["status"], "bootstrapped")
        self.assertEqual(boot["summary"]["mission"], "QNT30708")

        cycle = engine.strategy_evolution_engine_propose_cycle({"email": self.email, "name": "volatility regime update"})
        self.assertEqual(cycle["status"], "proposed")

        evaluated = engine.strategy_evolution_engine_evaluate({
            "email": self.email,
            "strategy_name": "adaptive-momentum-v3",
            "live_return_pct": 19.2,
            "live_sharpe": 1.72,
            "max_drawdown_pct": 5.1,
            "win_rate_pct": 58,
            "stability_score": 91,
            "coverage_score": 84,
        })
        self.assertEqual(evaluated["status"], "evaluated")
        self.assertIn("score", evaluated["candidate"]["latest_evaluation"])

        candidate_id = evaluated["candidate"]["candidate_id"]
        promote = engine.strategy_evolution_engine_promote({"email": self.email, "candidate_id": candidate_id, "action": "promote"})
        self.assertEqual(promote["status"], "processed")


if __name__ == "__main__":
    unittest.main()
