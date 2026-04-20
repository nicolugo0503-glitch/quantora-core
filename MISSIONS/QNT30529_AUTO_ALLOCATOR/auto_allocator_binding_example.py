# QNT30529 — Auto-allocator binding example

from fastapi import FastAPI

from MISSIONS.QNT30529_AUTO_ALLOCATOR.qnt30529_auto_allocator import QNT30529AutoAllocator
from MISSIONS.QNT30529_AUTO_ALLOCATOR.qnt30529_router import build_qnt30529_router

app = FastAPI()

engine = QNT30529AutoAllocator()
app.include_router(build_qnt30529_router(engine))
