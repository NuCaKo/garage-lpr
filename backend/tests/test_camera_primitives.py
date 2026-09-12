from pathlib import Path

from garage_lpr.camera.backoff import ReconnectBackoff
from garage_lpr.camera.buffer import LatestFrameBuffer
from garage_lpr.camera.contracts import CameraFrame
from garage_lpr.camera.secrets import SecretCipher


def _frame(sequence: int) -> CameraFrame:
    marker = object()
    return CameraFrame(
        image=marker,
        captured_monotonic_ns=sequence,
        sequence=sequence,
        width=1920,
        height=1080,
    )


def test_reconnect_backoff_caps_and_resets() -> None:
    backoff = ReconnectBackoff((1, 2, 5, 10, 30))

    assert [backoff.next_delay() for _ in range(7)] == [1, 2, 5, 10, 30, 30, 30]

    backoff.reset()
    assert backoff.next_delay() == 1


def test_latest_frame_wins_without_copying() -> None:
    buffer = LatestFrameBuffer()
    first = _frame(1)
    latest = _frame(2)

    buffer.put(first)
    buffer.put(latest)

    assert buffer.latest() is latest
    assert buffer.latest(after_sequence=2) is None
    assert buffer.replaced_frames == 1


def test_camera_password_is_encrypted_at_rest(tmp_path: Path) -> None:
    key_path = tmp_path / "camera.key"
    cipher = SecretCipher(key_path)

    encrypted = cipher.encrypt("garage-secret")

    assert b"garage-secret" not in encrypted
    assert cipher.decrypt(encrypted) == "garage-secret"
    assert key_path.stat().st_mode & 0o777 == 0o600
