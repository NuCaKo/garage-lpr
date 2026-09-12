import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from garage_lpr.api.dependencies import get_database_session
from garage_lpr.api.schemas.events import EventListRead, EventRead
from garage_lpr.auth.service import AuthenticationFailedError
from garage_lpr.database.repositories.events import EventRepository
from garage_lpr.events.types import EventType

router = APIRouter(tags=["events"])
websocket_router = APIRouter(tags=["events"])
HEARTBEAT_SECONDS = 30.0
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("/events", response_model=EventListRead)
def list_events(
    session: DatabaseSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    event_type: EventType | None = None,
    camera_id: int | None = Query(default=None, ge=1),
    plate: str | None = Query(default=None, max_length=24),
    status: str | None = Query(default=None, min_length=1, max_length=64),
) -> EventListRead:
    normalized_plate = re.sub(r"[\s.\-]", "", plate.upper()) if plate else None
    rows, total = EventRepository(session).list_recent(
        limit=limit,
        offset=offset,
        event_type=event_type,
        camera_id=camera_id,
        plate=normalized_plate,
        status=status.strip() if status else None,
    )
    return EventListRead(
        items=[EventRead.from_model(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@websocket_router.websocket("/events/live")
async def live_events(websocket: WebSocket) -> None:
    settings = websocket.app.state.settings
    origin = websocket.headers.get("origin")
    if origin and origin not in websocket.app.state.allowed_websocket_origins:
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    session = websocket.app.state.session_factory()
    try:
        principal = websocket.app.state.authentication_service.authenticate(
            session,
            websocket.cookies.get(settings.session_cookie_name),
        )
        if principal.role != "ADMIN":
            await websocket.close(code=4403, reason="Admin role required")
            return
    except AuthenticationFailedError:
        await websocket.close(code=4401, reason="Authentication required")
        return
    finally:
        session.close()
    await websocket.accept()
    broker = websocket.app.state.live_event_broker
    try:
        subscription = broker.subscribe()
    except RuntimeError:
        await websocket.close(code=1013, reason="Live event subscriber limit reached")
        return
    try:
        while True:
            try:
                event = await asyncio.wait_for(subscription.queue.get(), timeout=HEARTBEAT_SECONDS)
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                continue
            await websocket.send_json(EventRead.from_domain(event).model_dump(mode="json"))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        broker.unsubscribe(subscription.subscription_id)
