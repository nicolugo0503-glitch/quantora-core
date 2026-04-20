
from fastapi import APIRouter
from .revenue_activation import activation_metrics, revenue_metrics

router = APIRouter()

@router.get("/platform/metrics/activation")
def activation():
    return activation_metrics()

@router.get("/platform/metrics/revenue")
def revenue():
    return revenue_metrics()
