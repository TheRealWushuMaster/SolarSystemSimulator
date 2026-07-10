"""In-memory session registry -- single-process, no persistence.

A personal, single-user VPS deployment doesn't need cross-process session
sharing; if that ever changes, this is the seam where a Redis-backed
registry would replace the plain dict.
"""

from __future__ import annotations

import time
from typing import Any

from server.session import SolaraSession

# A dropped WebSocket (a network blip, a backgrounded tab) is common and
# should NOT destroy the session -- the frontend reconnects to the same
# session_id, and any REST call in flight when the socket dropped must still
# find it. Sessions are instead reaped lazily, on the next create_session
# call, once they've been unseen for MAX_IDLE_SECONDS (no client ever comes
# back to them). A single-process personal deployment doesn't need a real
# background sweep task for this.
MAX_IDLE_SECONDS: float = 30.0 * 60.0

# A public URL can be hit with a burst of POST /api/session calls faster than
# MAX_IDLE_SECONDS ever elapses, so the lazy idle sweep alone can't bound
# memory. Once at the cap, the oldest session (by last-seen) is evicted to
# make room -- simpler than rejecting with 429 for a single-user deployment.
MAX_SESSIONS: int = 50

_sessions: dict[str, SolaraSession] = {}
_last_seen: dict[str, float] = {}
_kernel: Any = None
_epoch_jd: float = 0.0


def configure(kernel: Any, epoch_jd: float) -> None:
    global _kernel, _epoch_jd
    _kernel = kernel
    _epoch_jd = epoch_jd


def create_session() -> SolaraSession:
    _sweep_idle()
    if len(_sessions) >= MAX_SESSIONS:
        oldest_id = min(_last_seen, key=lambda sid: _last_seen[sid])
        drop_session(oldest_id)
    # SolaraSession loads its own "now" at construction time -- _epoch_jd
    # here is only the fixed startup reference used for the shared,
    # cached orbit_lines (see static_data.orbit_lines).
    session = SolaraSession(kernel=_kernel)
    _sessions[session.session_id] = session
    _last_seen[session.session_id] = time.monotonic()
    return session


def get_session(session_id: str) -> SolaraSession | None:
    return _sessions.get(session_id)


def touch(session_id: str) -> None:
    """Mark a session as recently active (called on every WS message and
    REST command), so it survives disconnects but not true abandonment."""
    if session_id in _sessions:
        _last_seen[session_id] = time.monotonic()


def shared_kernel() -> Any:
    return _kernel


def shared_epoch_jd() -> float:
    return _epoch_jd


def drop_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _last_seen.pop(session_id, None)


def _sweep_idle() -> None:
    now = time.monotonic()
    stale = [sid for sid, seen in _last_seen.items() if now - seen > MAX_IDLE_SECONDS]
    for sid in stale:
        drop_session(sid)
