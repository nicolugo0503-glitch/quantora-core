# QNT30525 — Portfolio sync binding example
# Example only. Additive guidance, not auto-applied.

from fastapi import FastAPI

from MISSIONS.QNT30524_ALPACA_LIVE_BINDING.qnt30524_alpaca_engine import AlpacaBrokerAdapter
from MISSIONS.QNT30525_PORTFOLIO_STATE_SYNC_REAL_POSITION_TRACKING.qnt30525_portfolio_state_sync import QNT30525PortfolioStateSync
from MISSIONS.QNT30525_PORTFOLIO_STATE_SYNC_REAL_POSITION_TRACKING.qnt30525_router import build_qnt30525_router

app = FastAPI()

broker = AlpacaBrokerAdapter(
    api_key="YOUR_KEY",
    api_secret="YOUR_SECRET",
    base_url="https://paper-api.alpaca.markets",
)
engine = QNT30525PortfolioStateSync(broker_adapter=broker)
app.include_router(build_qnt30525_router(engine))
