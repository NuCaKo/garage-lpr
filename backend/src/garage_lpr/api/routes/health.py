from fastapi import APIRouter, Request

from garage_lpr.health.service import SystemHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SystemHealth)
def get_health(request: Request) -> SystemHealth:
    return request.app.state.health_service.snapshot()
