from enum import StrEnum


class EventType(StrEnum):
    CAMERA_CONNECTED = "camera_connected"
    CAMERA_DISCONNECTED = "camera_disconnected"
    PLATE_DETECTED = "plate_detected"
    PLATE_RECOGNIZED = "plate_recognized"
    RECOGNITION_ERROR = "recognition_error"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    GATE_OPEN_REQUESTED = "gate_open_requested"
    GATE_OPEN_SUCCESS = "gate_open_success"
    GATE_OPEN_FAILED = "gate_open_failed"
    SIMULATED_GATE_OPEN = "simulated_gate_open"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    ADMIN_CREATED = "admin_created"
    USER_LOGIN_SUCCESS = "user_login_success"
    USER_LOGIN_FAILED = "user_login_failed"
    USER_LOGOUT = "user_logout"
