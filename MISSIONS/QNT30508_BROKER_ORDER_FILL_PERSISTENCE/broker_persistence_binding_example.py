# QNT30508 — Broker persistence binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30508_BROKER_ORDER_FILL_PERSISTENCE.qnt30508_broker_persistence_store import QNT30508BrokerPersistenceStore
from MISSIONS.QNT30508_BROKER_ORDER_FILL_PERSISTENCE.qnt30508_broker_persistence_adapter import QNT30508BrokerPersistenceAdapter
from MISSIONS.QNT30508_BROKER_ORDER_FILL_PERSISTENCE.qnt30508_broker_persistence_router import build_qnt30508_router

app = FastAPI()

# Replace these with your real live objects
execution_bridge = None
alpaca_client = None

store = QNT30508BrokerPersistenceStore()
adapter = QNT30508BrokerPersistenceAdapter(store=store, execution_bridge=execution_bridge, alpaca_client=alpaca_client)

app.include_router(build_qnt30508_router(store, adapter))
