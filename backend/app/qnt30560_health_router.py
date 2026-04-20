from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    from backend.app import main as app_main
    return app_main.health()

@router.get("/health/attribution")
def health_attribution():
    from backend.app import main as app_main
    return app_main.health_attribution()

@router.get("/health/deployment")
def health_deployment():
    from backend.app import main as app_main
    return app_main.health_deployment()
