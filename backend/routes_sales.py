
from fastapi import APIRouter
from .sales_layer import demo_metrics, investor_pipeline

router = APIRouter()

@router.get("/platform/sales/demo")
def demo():
    return demo_metrics()

@router.get("/platform/sales/pipeline")
def pipeline():
    return investor_pipeline()
