from dataclasses import dataclass

from garage_lpr.detection.contracts import BoundingBox


@dataclass(frozen=True, slots=True)
class TrackerUpdate:
    track_ids: tuple[int, ...]
    active_track_ids: frozenset[int]


@dataclass(slots=True)
class _Track:
    track_id: int
    camera_id: int
    box: BoundingBox
    last_seen_ns: int


class IoUTracker:
    """Bounded, appearance-free tracker for short-lived plate observations."""

    def __init__(
        self,
        iou_threshold: float = 0.30,
        max_idle_ms: int = 1500,
        max_tracks: int = 128,
    ) -> None:
        if not 0 < iou_threshold <= 1:
            raise ValueError("IoU threshold must be within (0, 1]")
        if max_idle_ms < 1 or max_tracks < 1:
            raise ValueError("Tracker limits must be positive")
        self._iou_threshold = iou_threshold
        self._max_idle_ns = max_idle_ms * 1_000_000
        self._max_tracks = max_tracks
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1

    def update(
        self,
        camera_id: int,
        boxes: tuple[BoundingBox, ...],
        observed_ns: int,
    ) -> TrackerUpdate:
        self._prune(observed_ns)
        camera_tracks = [track for track in self._tracks.values() if track.camera_id == camera_id]
        candidates = sorted(
            (
                (_intersection_over_union(track.box, box), track.track_id, index)
                for track in camera_tracks
                for index, box in enumerate(boxes)
            ),
            reverse=True,
        )
        assigned_tracks: set[int] = set()
        assigned_boxes: set[int] = set()
        track_ids: list[int | None] = [None] * len(boxes)
        for score, track_id, box_index in candidates:
            if score < self._iou_threshold:
                break
            if track_id in assigned_tracks or box_index in assigned_boxes:
                continue
            track = self._tracks[track_id]
            track.box = boxes[box_index]
            track.last_seen_ns = observed_ns
            track_ids[box_index] = track_id
            assigned_tracks.add(track_id)
            assigned_boxes.add(box_index)

        for index, box in enumerate(boxes):
            if track_ids[index] is not None:
                continue
            self._ensure_capacity()
            track_id = self._next_track_id
            self._next_track_id += 1
            self._tracks[track_id] = _Track(track_id, camera_id, box, observed_ns)
            track_ids[index] = track_id

        active = frozenset(
            track.track_id for track in self._tracks.values() if track.camera_id == camera_id
        )
        resolved = tuple(track_id for track_id in track_ids if track_id is not None)
        if len(resolved) != len(boxes):
            raise RuntimeError("Tracker did not assign every detection")
        return TrackerUpdate(resolved, active)

    def _prune(self, observed_ns: int) -> None:
        expired = [
            track_id
            for track_id, track in self._tracks.items()
            if observed_ns - track.last_seen_ns > self._max_idle_ns
        ]
        for track_id in expired:
            self._tracks.pop(track_id, None)

    def _ensure_capacity(self) -> None:
        if len(self._tracks) < self._max_tracks:
            return
        oldest = min(self._tracks.values(), key=lambda track: track.last_seen_ns)
        self._tracks.pop(oldest.track_id, None)


def _intersection_over_union(first: BoundingBox, second: BoundingBox) -> float:
    width = max(0.0, min(first.x2, second.x2) - max(first.x1, second.x1))
    height = max(0.0, min(first.y2, second.y2) - max(first.y1, second.y1))
    intersection = width * height
    first_area = max(0.0, first.x2 - first.x1) * max(0.0, first.y2 - first.y1)
    second_area = max(0.0, second.x2 - second.x1) * max(0.0, second.y2 - second.y1)
    union = first_area + second_area - intersection
    return intersection / union if union > 0 else 0.0
