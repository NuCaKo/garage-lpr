from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.detection.sampler import FrameSampler


def _frame(sequence: int, timestamp_ns: int) -> CameraFrame:
    return CameraFrame(object(), timestamp_ns, sequence, 1280, 720)


def test_sampler_limits_detection_rate_without_queuing_frames() -> None:
    sampler = FrameSampler(detection_fps=5)

    assert sampler.should_process(_frame(1, 1_000_000_000)) is True
    assert sampler.should_process(_frame(2, 1_050_000_000)) is False
    assert sampler.should_process(_frame(3, 1_199_999_999)) is False
    assert sampler.should_process(_frame(4, 1_200_000_000)) is True


def test_sampler_recovers_when_monotonic_source_restarts() -> None:
    sampler = FrameSampler(detection_fps=5)

    assert sampler.should_process(_frame(1, 5_000_000_000)) is True
    assert sampler.should_process(_frame(2, 100)) is True
