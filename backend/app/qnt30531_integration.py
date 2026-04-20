import importlib.util
import sys
from pathlib import Path


def _root():
    return Path(__file__).resolve().parents[2]


def _load_module(unique_name: str, relative_path: str):
    path = _root() / relative_path
    spec = importlib.util.spec_from_file_location(unique_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def integrate_qnt30531(app):
    project_root = _root()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Core integrated missions
    m30505_router = _load_module("qnt30505_router", "MISSIONS/QNT30505_LIVE_VALIDATION_DIAGNOSTICS/qnt30505_diagnostics_router.py")
    m30506_sched = _load_module("qnt30506_sched", "MISSIONS/QNT30506_REAL_EXECUTION_LOOP_SCHEDULER/qnt30506_execution_loop_scheduler.py")
    m30506_router = _load_module("qnt30506_router", "MISSIONS/QNT30506_REAL_EXECUTION_LOOP_SCHEDULER/qnt30506_scheduler_router.py")
    m30507_store = _load_module("qnt30507_store", "MISSIONS/QNT30507_PERSISTENT_STATE_AUDIT_LOG/qnt30507_persistent_state_store.py")
    m30507_wrap = _load_module("qnt30507_wrap", "MISSIONS/QNT30507_PERSISTENT_STATE_AUDIT_LOG/qnt30507_persistent_scheduler_wrapper.py")
    m30507_router = _load_module("qnt30507_router", "MISSIONS/QNT30507_PERSISTENT_STATE_AUDIT_LOG/qnt30507_audit_router.py")
    m30508_store = _load_module("qnt30508_store", "MISSIONS/QNT30508_BROKER_ORDER_FILL_PERSISTENCE/qnt30508_broker_persistence_store.py")
    m30508_adapter = _load_module("qnt30508_adapter", "MISSIONS/QNT30508_BROKER_ORDER_FILL_PERSISTENCE/qnt30508_broker_persistence_adapter.py")
    m30508_router = _load_module("qnt30508_router", "MISSIONS/QNT30508_BROKER_ORDER_FILL_PERSISTENCE/qnt30508_broker_persistence_router.py")
    m30509 = _load_module("qnt30509", "MISSIONS/QNT30509_RISK_GUARDRAILS_LIVE_LOOP/qnt30509_risk_guardrails.py")
    m30509_router = _load_module("qnt30509_router", "MISSIONS/QNT30509_RISK_GUARDRAILS_LIVE_LOOP/qnt30509_risk_router.py")
    m30510_store = _load_module("qnt30510_store", "MISSIONS/QNT30510_AUTOMATED_NAV_REFRESH_EOD_SNAPSHOTS/qnt30510_nav_snapshot_store.py")
    m30510_service = _load_module("qnt30510_service", "MISSIONS/QNT30510_AUTOMATED_NAV_REFRESH_EOD_SNAPSHOTS/qnt30510_nav_refresh_service.py")
    m30510_router = _load_module("qnt30510_router", "MISSIONS/QNT30510_AUTOMATED_NAV_REFRESH_EOD_SNAPSHOTS/qnt30510_nav_router.py")
    m30511_engine = _load_module("qnt30511_engine", "MISSIONS/QNT30511_PORTFOLIO_RECON_DRIFT/qnt30511_reconciliation_engine.py")
    m30511_router = _load_module("qnt30511_router", "MISSIONS/QNT30511_PORTFOLIO_RECON_DRIFT/qnt30511_router.py")
    m30512_engine = _load_module("qnt30512_engine", "MISSIONS/QNT30512_AUTONOMOUS_REBALANCING_ENGINE/qnt30512_autonomous_rebalancing_engine.py")
    m30512_router = _load_module("qnt30512_router", "MISSIONS/QNT30512_AUTONOMOUS_REBALANCING_ENGINE/qnt30512_rebalance_router.py")
    m30513_engine = _load_module("qnt30513_engine", "MISSIONS/QNT30513_TREASURY_CASH_MANAGEMENT_LAYER/qnt30513_treasury_engine.py")
    m30513_router = _load_module("qnt30513_router", "MISSIONS/QNT30513_TREASURY_CASH_MANAGEMENT_LAYER/qnt30513_treasury_router.py")
    m30514_engine = _load_module("qnt30514_engine", "MISSIONS/QNT30514_CAPITAL_CALLS_REDEMPTION_WORKFLOW/qnt30514_capital_workflow_engine.py")
    m30514_router = _load_module("qnt30514_router", "MISSIONS/QNT30514_CAPITAL_CALLS_REDEMPTION_WORKFLOW/qnt30514_capital_workflow_router.py")
    m30515_engine = _load_module("qnt30515_engine", "MISSIONS/QNT30515_INVESTOR_STATEMENTS_DISTRIBUTIONS/qnt30515_reporting_engine.py")
    m30515_router = _load_module("qnt30515_router", "MISSIONS/QNT30515_INVESTOR_STATEMENTS_DISTRIBUTIONS/qnt30515_router.py")
    m30516_engine = _load_module("qnt30516_engine", "MISSIONS/QNT30516_FEE_ENGINE/qnt30516_fee_engine.py")
    m30516_router = _load_module("qnt30516_router", "MISSIONS/QNT30516_FEE_ENGINE/qnt30516_router.py")
    m30517_engine = _load_module("qnt30517_engine", "MISSIONS/QNT30517_MULTI_FUND_MULTI_PORTFOLIO_LAYER/qnt30517_multi_fund_engine.py")
    m30517_router = _load_module("qnt30517_router", "MISSIONS/QNT30517_MULTI_FUND_MULTI_PORTFOLIO_LAYER/qnt30517_multi_fund_router.py")
    m30518_engine = _load_module("qnt30518_engine", "MISSIONS/QNT30518_INVESTOR_ONBOARDING_SUBSCRIPTION_WORKFLOW/qnt30518_onboarding_engine.py")
    m30518_router = _load_module("qnt30518_router", "MISSIONS/QNT30518_INVESTOR_ONBOARDING_SUBSCRIPTION_WORKFLOW/qnt30518_onboarding_router.py")
    m30520_engine = _load_module("qnt30520_engine", "MISSIONS/QNT30520_LIVE_CAPITAL_ALLOCATION_BRAIN/qnt30520_allocation_brain.py")
    m30520_router = _load_module("qnt30520_router", "MISSIONS/QNT30520_LIVE_CAPITAL_ALLOCATION_BRAIN/qnt30520_router.py")
    m30521_engine = _load_module("qnt30521_engine", "MISSIONS/QNT30521_ADAPTIVE_AI_ALLOCATION/qnt30521_engine.py")
    m30521_router = _load_module("qnt30521_router", "MISSIONS/QNT30521_ADAPTIVE_AI_ALLOCATION/qnt30521_router.py")
    m30522_engine = _load_module("qnt30522_engine", "MISSIONS/QNT30522_CLOSED_LOOP_AUTONOMOUS_FUND/qnt30522_closed_loop_fund.py")
    m30522_router = _load_module("qnt30522_router", "MISSIONS/QNT30522_CLOSED_LOOP_AUTONOMOUS_FUND/qnt30522_router.py")
    m30523_engine = _load_module("qnt30523_engine", "MISSIONS/QNT30523_LIVE_EXECUTION_ROUTING/qnt30523_execution_engine.py")
    m30523_router = _load_module("qnt30523_router", "MISSIONS/QNT30523_LIVE_EXECUTION_ROUTING/qnt30523_router.py")
    m30524_engine = _load_module("qnt30524_engine", "MISSIONS/QNT30524_ALPACA_LIVE_BINDING/qnt30524_alpaca_engine.py")
    m30524_router = _load_module("qnt30524_router", "MISSIONS/QNT30524_ALPACA_LIVE_BINDING/qnt30524_router.py")
    m30525_engine = _load_module("qnt30525_engine", "MISSIONS/QNT30525_PORTFOLIO_STATE_SYNC_REAL_POSITION_TRACKING/qnt30525_portfolio_state_sync.py")
    m30525_router = _load_module("qnt30525_router", "MISSIONS/QNT30525_PORTFOLIO_STATE_SYNC_REAL_POSITION_TRACKING/qnt30525_router.py")
    m30526_engine = _load_module("qnt30526_engine", "MISSIONS/QNT30526_RISK_GOVERNOR_KILL_SWITCH/qnt30526_risk_engine.py")
    m30526_router = _load_module("qnt30526_router", "MISSIONS/QNT30526_RISK_GOVERNOR_KILL_SWITCH/qnt30526_router.py")
    m30527_engine = _load_module("qnt30527_engine", "MISSIONS/QNT30527_STRATEGY_MARKETPLACE/qnt30527_engine.py")
    m30527_router = _load_module("qnt30527_router", "MISSIONS/QNT30527_STRATEGY_MARKETPLACE/qnt30527_router.py")
    m30528_engine = _load_module("qnt30528_engine", "MISSIONS/QNT30528_STRATEGY_SCORING_RANKING/qnt30528_engine.py")
    m30528_router = _load_module("qnt30528_router", "MISSIONS/QNT30528_STRATEGY_SCORING_RANKING/qnt30528_router.py")
    m30529_engine = _load_module("qnt30529_engine", "MISSIONS/QNT30529_AUTO_ALLOCATOR/qnt30529_auto_allocator.py")
    m30529_router = _load_module("qnt30529_router", "MISSIONS/QNT30529_AUTO_ALLOCATOR/qnt30529_router.py")
    m30530_engine = _load_module("qnt30530_engine", "MISSIONS/QNT30530_LIVE_FUND_MODE/qnt30530_live_fund.py")
    m30530_router = _load_module("qnt30530_router", "MISSIONS/QNT30530_LIVE_FUND_MODE/qnt30530_router.py")

    # Optional newer missions
    signal_engine = None
    performance_engine = None
    if (_root() / "MISSIONS/QNT30533_SIGNAL_ENGINE/qnt30533_signal_engine.py").exists():
        m30533_engine = _load_module("qnt30533_engine", "MISSIONS/QNT30533_SIGNAL_ENGINE/qnt30533_signal_engine.py")
        m30533_router = _load_module("qnt30533_router", "MISSIONS/QNT30533_SIGNAL_ENGINE/qnt30533_router.py")
        signal_engine = m30533_engine.QNT30533SignalEngine()
        app.include_router(m30533_router.build_qnt30533_router(signal_engine))

    if (_root() / "MISSIONS/QNT30534_PERFORMANCE_PNL_ENGINE/qnt30534_performance_engine.py").exists():
        m30534_engine = _load_module("qnt30534_engine", "MISSIONS/QNT30534_PERFORMANCE_PNL_ENGINE/qnt30534_performance_engine.py")
        m30534_router = _load_module("qnt30534_router", "MISSIONS/QNT30534_PERFORMANCE_PNL_ENGINE/qnt30534_router.py")
        performance_engine = m30534_engine.QNT30534PerformanceEngine()
        app.include_router(m30534_router.build_qnt30534_router(performance_engine))

    # Build shared runtime objects
    broker = m30524_engine.AlpacaBrokerAdapter()
    live_execution = m30524_engine.QNT30524LiveExecution(broker)
    portfolio_sync = m30525_engine.QNT30525PortfolioStateSync(broker_adapter=broker)
    risk_governor = m30526_engine.QNT30526RiskGovernor()
    allocation_brain = m30520_engine.QNT30520AllocationBrain()
    adaptive_engine = m30521_engine.QNT30521AdaptiveEngine()
    closed_loop = m30522_engine.QNT30522ClosedLoopFund(
        allocation_brain=allocation_brain,
        adaptive_engine=adaptive_engine,
        broker_adapter=broker,
    )
    execution_engine = m30523_engine.QNT30523ExecutionEngine(broker=broker)
    live_fund = m30530_engine.QNT30530LiveFund(closed_loop=closed_loop, risk=risk_governor)
    scoring_engine = m30528_engine.QNT30528ScoringEngine()
    auto_allocator = m30529_engine.QNT30529AutoAllocator(scorer=scoring_engine)

    scheduler = m30506_sched.QNT30506ExecutionLoopScheduler(state_adapter=None, cycle_runner=None, interval_seconds=5.0)
    persistent_store = m30507_store.QNT30507PersistentStateStore()
    persistent_scheduler = m30507_wrap.QNT30507PersistentSchedulerWrapper(scheduler, persistent_store)
    persistent_scheduler.recover()

    broker_store = m30508_store.QNT30508BrokerPersistenceStore()
    broker_persist_adapter = m30508_adapter.QNT30508BrokerPersistenceAdapter(store=broker_store, execution_bridge=None, alpaca_client=broker)

    nav_store = m30510_store.QNT30510NAVSnapshotStore()
    nav_service = m30510_service.QNT30510NAVRefreshService(store=nav_store, nav_engine=None, active_fund_id="FUND1")
    recon_engine = m30511_engine.QNT30511ReconciliationEngine()
    rebalance_engine = m30512_engine.QNT30512AutonomousRebalancingEngine(drift_tolerance_pct=2.0)
    rebalance_executor = m30512_engine.QNT30512RebalanceExecutionAdapter(rebalance_engine, broker_adapter=broker)
    treasury_engine = m30513_engine.QNT30513TreasuryEngine()
    capital_engine = m30514_engine.QNT30514CapitalWorkflowEngine()
    reporting_engine = m30515_engine.QNT30515InvestorReportingEngine()
    fee_engine = m30516_engine.QNT30516FeeEngine()
    multifund_engine = m30517_engine.QNT30517MultiFundEngine()
    onboarding_engine = m30518_engine.QNT30518InvestorOnboardingEngine()
    marketplace_engine = m30527_engine.QNT30527Marketplace()

    diagnostics_adapter = m30505_router.QNT30505DiagnosticsAdapter(portfolio_sync)

    # Mount routers
    app.include_router(m30505_router.build_qnt30505_router(diagnostics_adapter))
    app.include_router(m30506_router.build_qnt30506_router(persistent_scheduler))
    app.include_router(m30507_router.build_qnt30507_router(persistent_store))
    app.include_router(m30508_router.build_qnt30508_router(broker_store, broker_persist_adapter))
    app.include_router(m30509_router.build_qnt30509_router(risk_governor))
    app.include_router(m30510_router.build_qnt30510_router(nav_store, nav_service))
    app.include_router(m30511_router.build_qnt30511_router(recon_engine))
    app.include_router(m30512_router.build_qnt30512_router(rebalance_engine, rebalance_executor))
    app.include_router(m30513_router.build_qnt30513_router(treasury_engine))
    app.include_router(m30514_router.build_qnt30514_router(capital_engine))
    app.include_router(m30515_router.build_qnt30515_router(reporting_engine))
    app.include_router(m30516_router.build_qnt30516_router(fee_engine))
    app.include_router(m30517_router.build_qnt30517_router(multifund_engine))
    app.include_router(m30518_router.build_qnt30518_router(onboarding_engine))
    app.include_router(m30520_router.build_qnt30520_router(allocation_brain))
    app.include_router(m30521_router.build_qnt30521_router(adaptive_engine))
    app.include_router(m30522_router.build_qnt30522_router(closed_loop))
    app.include_router(m30523_router.build_qnt30523_router(execution_engine))
    app.include_router(m30524_router.build_qnt30524_router(live_execution))
    app.include_router(m30525_router.build_qnt30525_router(portfolio_sync))
    app.include_router(m30526_router.build_qnt30526_router(risk_governor))
    app.include_router(m30527_router.build_qnt30527_router(marketplace_engine))
    app.include_router(m30528_router.build_qnt30528_router(scoring_engine))
    app.include_router(m30529_router.build_qnt30529_router(auto_allocator))
    app.include_router(m30530_router.build_qnt30530_router(live_fund))

    @app.get("/api/audit/qnt30531-smoke")
    def qnt30531_smoke():
        integrated = [
            "QNT30505","QNT30506","QNT30507","QNT30508","QNT30509","QNT30510",
            "QNT30511","QNT30512","QNT30513","QNT30514","QNT30515","QNT30516",
            "QNT30517","QNT30518","QNT30520","QNT30521","QNT30522","QNT30523",
            "QNT30524","QNT30525","QNT30526","QNT30527","QNT30528","QNT30529","QNT30530"
        ]
        if signal_engine is not None:
            integrated.append("QNT30533")
        if performance_engine is not None:
            integrated.append("QNT30534")
        return {"status": "ok", "integrated": integrated}
