# QNT30334 Notes

This build extends the uploaded QNT30333 package with:
- execution history recording
- per-operator attribution summaries
- broker-reconciled realized PnL aggregation

To wire fully in production:
- mount `backend/routes_execution_history.py` in the main app
- feed broker fills and close events into `/execution-history/record`
- merge `/execution-history/reconcile` output into the performance engine
- expose operator attribution in the multi-operator leaderboard
