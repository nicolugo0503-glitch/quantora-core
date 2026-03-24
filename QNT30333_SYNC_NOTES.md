# QNT30333 Broker Fill + PnL Sync Notes

This build extends the uploaded QNT30332 package with:
- broker fill recording
- broker-backed unrealized PnL snapshots
- fill stream endpoints

To wire fully in production:
- mount `backend/routes_broker_sync.py` in the main app
- connect Alpaca order/fill events to `/broker-sync/record-fill`
- feed live market prices into `/broker-sync/sync-pnl`
- merge snapshots into the existing performance engine and operator workspace
