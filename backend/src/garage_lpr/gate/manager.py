from contextlib import suppress
from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread

from garage_lpr.gate.contracts import GateCommandResult, GateController, GateState
from garage_lpr.gate.domain import GateRuntimeConfiguration, GateRuntimeSnapshot
from garage_lpr.gate.factory import GateControllerFactory


@dataclass(slots=True)
class _OpenCommand:
    controller: GateController
    completed: Event
    result: GateCommandResult | None = None
    error_type: str | None = None


class GateCommandExecutor:
    """Owns one bounded daemon worker; a timed-out adapter poisons further commands."""

    def __init__(self) -> None:
        self._queue: Queue[_OpenCommand | None] = Queue(maxsize=1)
        self._lock = Lock()
        self._busy = False
        self._poisoned = False
        self._stopped = False
        self._thread = Thread(target=self._run, name="gate-command-worker", daemon=True)
        self._thread.start()

    def open(self, controller: GateController, timeout_seconds: float) -> GateCommandResult:
        with self._lock:
            if self._stopped:
                return GateCommandResult(False, "GATE_EXECUTOR_STOPPED")
            if self._poisoned:
                return GateCommandResult(False, "GATE_EXECUTOR_POISONED")
            if self._busy:
                return GateCommandResult(False, "GATE_EXECUTOR_BUSY")
            self._busy = True
        command = _OpenCommand(controller=controller, completed=Event())
        try:
            self._queue.put_nowait(command)
        except Full:
            with self._lock:
                self._busy = False
            return GateCommandResult(False, "GATE_EXECUTOR_BUSY")
        if not command.completed.wait(timeout_seconds):
            with self._lock:
                self._poisoned = True
            return GateCommandResult(False, "GATE_COMMAND_TIMEOUT")
        if command.error_type is not None:
            return GateCommandResult(False, f"GATE_COMMAND_ERROR:{command.error_type}")
        return command.result or GateCommandResult(False, "GATE_COMMAND_NO_RESULT")

    @property
    def poisoned(self) -> bool:
        with self._lock:
            return self._poisoned

    def shutdown(self) -> None:
        with self._lock:
            self._stopped = True
        with suppress(Full):
            self._queue.put_nowait(None)
        self._thread.join(timeout=0.5)

    def _run(self) -> None:
        while True:
            try:
                command = self._queue.get(timeout=1.0)
            except Empty:
                with self._lock:
                    if self._stopped:
                        return
                continue
            if command is None:
                return
            try:
                command.result = command.controller.open()
            except Exception as error:
                command.error_type = type(error).__name__
            finally:
                with self._lock:
                    self._busy = False
                command.completed.set()


class GateManager:
    """Maintains active controller adapters and the application's sole open worker."""

    def __init__(self, factory: GateControllerFactory | None = None) -> None:
        self._factory = factory or GateControllerFactory()
        self._controllers: dict[int, GateController] = {}
        self._lock = Lock()
        self._executor: GateCommandExecutor | None = None

    def apply(self, configuration: GateRuntimeConfiguration) -> None:
        controller = self._factory.create(configuration)
        with self._lock:
            self._controllers[configuration.gate_controller_id] = controller
            if self._executor is None:
                self._executor = GateCommandExecutor()

    def remove(self, gate_controller_id: int) -> None:
        with self._lock:
            self._controllers.pop(gate_controller_id, None)
            executor = self._executor if not self._controllers else None
            if executor is not None:
                self._executor = None
        if executor is not None:
            executor.shutdown()

    def open(self, gate_controller_id: int, timeout_seconds: float) -> GateCommandResult:
        with self._lock:
            controller = self._controllers.get(gate_controller_id)
            executor = self._executor
        if controller is None or executor is None:
            return GateCommandResult(False, "GATE_CONTROLLER_NOT_ACTIVE")
        try:
            if not controller.health_check():
                return GateCommandResult(False, "GATE_CONTROLLER_UNHEALTHY")
        except Exception as error:
            return GateCommandResult(False, f"GATE_HEALTH_ERROR:{type(error).__name__}")
        return executor.open(controller, timeout_seconds)

    def snapshot(self, gate_controller_id: int) -> GateRuntimeSnapshot:
        with self._lock:
            controller = self._controllers.get(gate_controller_id)
            executor = self._executor
        if controller is None:
            return GateRuntimeSnapshot(
                gate_controller_id, GateState.UNAVAILABLE, False, "Controller is not active"
            )
        if executor is None or executor.poisoned:
            detail = (
                "Command executor is unavailable"
                if executor is None
                else "Command executor is poisoned after a timeout"
            )
            return GateRuntimeSnapshot(gate_controller_id, GateState.UNAVAILABLE, False, detail)
        try:
            healthy = controller.health_check()
            state = controller.status() if healthy else GateState.UNAVAILABLE
            detail = "Controller is available" if healthy else "Health check failed"
        except Exception as error:
            healthy = False
            state = GateState.UNAVAILABLE
            detail = f"Health check error: {type(error).__name__}"
        return GateRuntimeSnapshot(gate_controller_id, state, healthy, detail)

    def snapshots(self) -> tuple[GateRuntimeSnapshot, ...]:
        with self._lock:
            controller_ids = tuple(self._controllers)
        return tuple(self.snapshot(controller_id) for controller_id in controller_ids)

    def shutdown(self) -> None:
        with self._lock:
            executor = self._executor
            self._executor = None
            self._controllers.clear()
        if executor is not None:
            executor.shutdown()
