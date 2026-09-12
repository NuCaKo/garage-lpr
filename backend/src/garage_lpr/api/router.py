from fastapi import APIRouter, Depends

from garage_lpr.api.dependencies import require_admin
from garage_lpr.api.routes import (
    access_rules,
    auth,
    cameras,
    events,
    gates,
    health,
    metrics,
    settings,
    vehicles,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)

protected_router = APIRouter(dependencies=[Depends(require_admin)])
protected_router.include_router(health.router)
protected_router.include_router(settings.router)
protected_router.include_router(cameras.router)
protected_router.include_router(metrics.router)
protected_router.include_router(vehicles.router)
protected_router.include_router(gates.router)
protected_router.include_router(access_rules.router)
protected_router.include_router(events.router)
api_router.include_router(protected_router)
api_router.include_router(events.websocket_router)
