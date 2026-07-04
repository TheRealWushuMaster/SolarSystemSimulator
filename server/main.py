"""FastAPI app entry point. Opens the 146MB SPK kernel once at startup and
shares it (read-only) across every session -- mirrors app.py's main()."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jplephem.spk import SPK

from config import EPHEMERIS_FILE
from core.time import convert_to_julian_date
from server import session_manager
from server.routes import router
from server.ws import session_socket

_kernel: SPK | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _kernel
    _kernel = SPK.open(EPHEMERIS_FILE)
    session_manager.configure(kernel=_kernel, epoch_jd=convert_to_julian_date(datetime.now()))
    try:
        yield
    finally:
        _kernel.close()


app = FastAPI(title="Solara", lifespan=lifespan)

# Vite's dev server runs on a different origin than uvicorn, so local dev
# needs CORS open to it; in production the Nginx deploy (see deploy/) serves
# the built frontend and proxies /api + /ws from the SAME origin, so CORS
# isn't even exercised there -- ALLOWED_ORIGINS just needs to cover dev and
# any origin actually serving the frontend from a different host.
_allowed_origins: list[str] = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.websocket("/ws/session/{session_id}")(session_socket)
