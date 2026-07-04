"""WebSocket route: per-tick advance + control messages (see plan section on
the REST/WebSocket split -- anything tied to the render loop's cadence lives
here rather than as a REST round trip)."""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from server import session_manager
from server.serialization import state_message


async def session_socket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = session_manager.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="unknown session")
        return
    last_trail_len = 0
    try:
        while True:
            message: dict[str, Any] = await websocket.receive_json()
            session_manager.touch(session_id)
            _dispatch(session, message)
            points = session.trail.points
            # A mission/home change replaces `trail` with a fresh TrailPath
            # (see session.py's set_home/_launch_mission/load_mission), which
            # this detects as a shrink -- the client must clear its retained
            # buffer and re-seed it with the full (usually tiny) new one,
            # rather than appending on top of stale points from the old flight.
            reset = len(points) < last_trail_len
            trail_append = points if reset else points[last_trail_len:]
            last_trail_len = len(points)
            await websocket.send_json(state_message(session, trail_append, reset))
    except WebSocketDisconnect:
        pass   # the session survives -- see session_manager's idle sweep


def _dispatch(session: Any, message: dict[str, Any]) -> None:
    msg_type: str = message.get("type", "")
    if msg_type == "tick":
        if session.auto_play:
            session.advance(session.time_step_s * session.play_direction)
    elif msg_type == "step":
        direction: float = float(message.get("direction", 1.0))
        session.advance(session.time_step_s * direction)
    elif msg_type == "set_play":
        session.set_play(bool(message.get("playing", False)))
    elif msg_type == "reverse":
        session.reverse()
    elif msg_type == "set_time_step":
        session.set_time_step(int(message.get("index", session.time_step_index)))
    elif msg_type == "set_follow":
        session.set_follow(str(message.get("target", session.follow_target)))
    elif msg_type == "toggle_test_drive":
        session.toggle_test_drive()
