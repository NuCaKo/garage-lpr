from dataclasses import asdict

from fastapi import APIRouter, Request

from garage_lpr.api.schemas.metrics import InferenceMetricsRead, ResourceMetricsRead

router = APIRouter(tags=["metrics"])


@router.get("/metrics/inference", response_model=InferenceMetricsRead)
def get_inference_metrics(request: Request) -> InferenceMetricsRead:
    snapshot = request.app.state.inference_manager.snapshot()
    return InferenceMetricsRead.model_validate(asdict(snapshot))


@router.get("/metrics/resources", response_model=ResourceMetricsRead)
def get_resource_metrics(request: Request) -> ResourceMetricsRead:
    snapshot = request.app.state.resource_monitor.snapshot()
    return ResourceMetricsRead.model_validate(asdict(snapshot))
