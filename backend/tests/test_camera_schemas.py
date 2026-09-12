import pytest
from pydantic import ValidationError

from garage_lpr.api.schemas.cameras import CameraCreate, NormalizedROISchema


def test_camera_schema_rejects_credentials_in_url() -> None:
    with pytest.raises(ValidationError):
        CameraCreate(name="Giriş", stream_url="rtsp://admin:secret@camera.local/live")


def test_roi_must_remain_inside_frame() -> None:
    with pytest.raises(ValidationError):
        NormalizedROISchema(x=0.8, y=0.1, width=0.3, height=0.5)


def test_detection_fps_cannot_exceed_capture_limit() -> None:
    with pytest.raises(ValidationError):
        CameraCreate(
            name="Giriş",
            stream_url="rtsp://camera.local/live",
            capture_fps_limit=3,
            detection_fps=5,
        )
