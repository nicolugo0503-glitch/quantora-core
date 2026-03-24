# QNT30332 Broker Governance Notes

This build extends the uploaded QNT30331 package with a governed broker-execution layer.

Included foundations:
- governed order-routing endpoint
- TP/SL evaluation endpoint
- broker position sync helper
- execution log stream

Before enabling live broker routing in production:
- mount `backend/routes_live_broker.py` in the main app
- connect order routing to existing Alpaca credentials
- keep governance approval required before live order submission
- keep kill switch as the final override
