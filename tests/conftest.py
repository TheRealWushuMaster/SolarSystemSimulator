"""Shared fixtures for the server-level tests (tests/test_server_*.py)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server import session_manager
from server.routes import router
from server.session import SolaraSession
from server.ws import session_socket
from tests.fake_kernel import FakeSpkKernel


@pytest.fixture
def fake_spk_kernel() -> FakeSpkKernel:
    """A kernel that answers for every chain in data/bodies.json."""
    return FakeSpkKernel()


@pytest.fixture
def session(fake_spk_kernel: FakeSpkKernel) -> SolaraSession:
    """A standalone session, not registered with the session manager."""
    return SolaraSession(kernel=fake_spk_kernel)


@pytest.fixture(autouse=True)
def clean_registry() -> Iterator[None]:
    """
    Reset `session_manager`'s module-level registry around every test.

    The registry is deliberately process-global (see its module docstring),
    so without this a session created by one test would count against
    another's MAX_SESSIONS assertions.
    """
    session_manager._sessions.clear()
    session_manager._last_seen.clear()
    yield
    session_manager._sessions.clear()
    session_manager._last_seen.clear()


@pytest.fixture
def api_client(fake_spk_kernel: FakeSpkKernel) -> Iterator[TestClient]:
    """
    A client over the real routes, but without `server.main`'s lifespan.

    `main.lifespan` opens the real de440t.bsp, which is gitignored and absent
    in CI. Mounting the same router and WebSocket handler onto a bare app and
    configuring the registry by hand exercises the identical request path
    with a fake kernel behind it.
    """
    app = FastAPI()
    app.include_router(router)
    app.websocket("/ws/session/{session_id}")(session_socket)
    session_manager.configure(kernel=fake_spk_kernel,
                              epoch_jd=fake_spk_kernel.epoch_jd)
    with TestClient(app=app) as client:
        yield client
    session_manager.configure(kernel=None,
                              epoch_jd=0.0)
