from garage_lpr.camera.domain import CameraRuntimeConfiguration, NormalizedROI
from garage_lpr.camera.secrets import SecretCipher
from garage_lpr.database.models import Camera
from garage_lpr.database.repositories.cameras import CameraRepository
from garage_lpr.inference.domain import InferenceCameraConfiguration


class CameraLimitError(ValueError):
    pass


class CameraService:
    def __init__(
        self,
        repository: CameraRepository,
        cipher: SecretCipher,
        max_active_cameras: int,
    ) -> None:
        self._repository = repository
        self._cipher = cipher
        self._max_active_cameras = max_active_cameras

    def list_all(self) -> list[Camera]:
        return self._repository.list_all()

    def get(self, camera_id: int) -> Camera | None:
        return self._repository.get(camera_id)

    def create(self, values: dict[str, object], password: str | None) -> Camera:
        self._check_active_limit(bool(values.get("active")))
        camera = Camera(**values)
        if password:
            camera.credentials_ciphertext = self._cipher.encrypt(password)
        return self._repository.add(camera)

    def update(
        self,
        camera: Camera,
        values: dict[str, object],
        password: str | None,
        clear_password: bool,
    ) -> Camera:
        becoming_active = bool(values.get("active", camera.active))
        if becoming_active:
            self._check_active_limit(True, excluding_id=camera.id)
        for name, value in values.items():
            setattr(camera, name, value)
        if clear_password:
            camera.credentials_ciphertext = None
        elif password:
            camera.credentials_ciphertext = self._cipher.encrypt(password)
        return self._repository.save(camera)

    def delete(self, camera: Camera) -> None:
        self._repository.delete(camera)

    def runtime_configuration(self, camera: Camera) -> CameraRuntimeConfiguration:
        return CameraRuntimeConfiguration(
            camera_id=camera.id,
            stream_url=camera.stream_url,
            username=camera.username,
            password=self._cipher.decrypt(camera.credentials_ciphertext),
            capture_fps_limit=camera.capture_fps_limit,
            requested_width=camera.requested_width,
            requested_height=camera.requested_height,
            connection_timeout_seconds=camera.connection_timeout_seconds,
            reconnect_schedule_seconds=tuple(camera.reconnect_schedule_seconds),
        )

    @staticmethod
    def roi(camera: Camera) -> NormalizedROI:
        return NormalizedROI(**camera.roi) if camera.roi else NormalizedROI()

    @classmethod
    def inference_configuration(cls, camera: Camera) -> InferenceCameraConfiguration:
        return InferenceCameraConfiguration(
            camera_id=camera.id,
            active=camera.active,
            detection_fps=camera.detection_fps,
            roi=cls.roi(camera),
        )

    def _check_active_limit(self, active: bool, excluding_id: int | None = None) -> None:
        if active and self._repository.count_active(excluding_id) >= self._max_active_cameras:
            raise CameraLimitError(f"At most {self._max_active_cameras} camera(s) can be active")
