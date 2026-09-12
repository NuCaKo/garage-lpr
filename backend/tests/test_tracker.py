from garage_lpr.detection.contracts import BoundingBox
from garage_lpr.recognition.tracker import IoUTracker


def test_iou_tracker_reuses_identity_and_expires_stale_track() -> None:
    tracker = IoUTracker(iou_threshold=0.3, max_idle_ms=1000, max_tracks=8)

    first = tracker.update(1, (BoundingBox(10, 10, 110, 60),), 0)
    second = tracker.update(1, (BoundingBox(15, 12, 115, 62),), 200_000_000)
    expired = tracker.update(1, (BoundingBox(15, 12, 115, 62),), 1_500_000_000)

    assert first.track_ids == second.track_ids
    assert expired.track_ids != first.track_ids
    assert len(expired.active_track_ids) == 1


def test_iou_tracker_does_not_share_tracks_between_cameras() -> None:
    tracker = IoUTracker(max_tracks=8)
    box = BoundingBox(0, 0, 100, 50)

    entrance = tracker.update(1, (box,), 0)
    exit_camera = tracker.update(2, (box,), 0)

    assert entrance.track_ids != exit_camera.track_ids
