"""REST routes: static catalogues, session lifecycle, and the one-shot
mission menu actions (fly_to/set_home/load_mission/export)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from server import session_manager, static_data

router = APIRouter()


def _require_session(session_id: str):
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session")
    session_manager.touch(session_id)
    return session


@router.get("/api/bodies")
def get_bodies() -> dict:
    return static_data.body_catalogue()


@router.get("/api/missions")
def get_missions() -> dict:
    return static_data.mission_catalogue()


@router.get("/api/orbit_lines")
def get_orbit_lines() -> dict:
    return static_data.orbit_lines(session_manager.shared_kernel(), session_manager.shared_epoch_jd())


@router.post("/api/session")
def create_session() -> dict:
    session = session_manager.create_session()
    return {"session_id": session.session_id}


@router.post("/api/session/{session_id}/set_home")
def set_home(session_id: str, body: dict) -> dict:
    session = _require_session(session_id)
    if not session.set_home(str(body.get("body", ""))):
        raise HTTPException(status_code=400, detail="unknown body")
    return {"status": "ok", "home_body": session.home_body}


@router.post("/api/session/{session_id}/fly_to")
def fly_to(session_id: str, body: dict) -> dict:
    session = _require_session(session_id)
    return session.fly_to(str(body.get("target", "")))


@router.post("/api/session/{session_id}/load_mission")
def load_mission(session_id: str, body: dict) -> dict:
    session = _require_session(session_id)
    result = session.load_mission(str(body.get("name", "")))
    if result["status"] == "unknown_mission":
        raise HTTPException(status_code=400, detail="unknown mission")
    return result


@router.post("/api/session/{session_id}/export")
def export_trajectory(session_id: str):
    session = _require_session(session_id)
    result = session.export_trajectory()
    if result["status"] != "ok":
        raise HTTPException(status_code=400, detail=result.get("message", "export failed"))
    with open(result["path"], encoding="utf-8") as handle:
        csv_text = handle.read()
    return PlainTextResponse(csv_text, media_type="text/csv")


@router.delete("/api/session/{session_id}")
def delete_session(session_id: str) -> dict:
    if session_manager.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="unknown session")
    session_manager.drop_session(session_id)
    return {"status": "ok"}
