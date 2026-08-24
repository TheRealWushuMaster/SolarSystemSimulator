"""
The in-memory session registry.

The two bounds here are what keep a public, unauthenticated URL from growing
without limit: a hard cap on live sessions (with least-recently-seen
eviction) and a lazy idle sweep. Both are exercised against monkeypatched
limits rather than the production values, so the tests stay fast and state
which bound they are checking.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from server import session_manager
from server.session import SolaraSession
from tests.fake_kernel import FakeSpkKernel


@pytest.fixture(autouse=True)
def configured_registry(fake_spk_kernel: FakeSpkKernel) -> Iterator[None]:
    session_manager.configure(kernel=fake_spk_kernel,
                              epoch_jd=fake_spk_kernel.epoch_jd)
    yield
    session_manager.configure(kernel=None,
                              epoch_jd=0.0)


class TestLifecycle:
    def test_create_registers_a_retrievable_session(self) -> None:
        created: SolaraSession = session_manager.create_session()
        assert session_manager.get_session(created.session_id) is created

    def test_get_unknown_session_returns_none(self) -> None:
        assert session_manager.get_session(session_id="does-not-exist") is None

    def test_drop_removes_the_session(self) -> None:
        created = session_manager.create_session()
        session_manager.drop_session(created.session_id)
        assert session_manager.get_session(created.session_id) is None

    def test_drop_is_idempotent(self) -> None:
        """The DELETE route and the idle sweep can both target the same id."""
        created = session_manager.create_session()
        session_manager.drop_session(created.session_id)
        session_manager.drop_session(created.session_id)   # must not raise

    def test_touch_of_an_unknown_session_is_ignored(self) -> None:
        """A WS message can arrive for a session the sweep just evicted; that
        must not resurrect a `_last_seen` entry with no session behind it."""
        session_manager.touch(session_id="does-not-exist")
        assert session_manager._last_seen == {}

    def test_sessions_are_built_with_the_configured_kernel(self,
                                                           fake_spk_kernel: FakeSpkKernel
                                                           ) -> None:
        created = session_manager.create_session()
        assert created.ephemeris.kernel is fake_spk_kernel

    def test_shared_accessors_return_the_configured_values(self,
                                                           fake_spk_kernel: FakeSpkKernel
                                                           ) -> None:
        assert session_manager.shared_kernel() is fake_spk_kernel
        assert session_manager.shared_epoch_jd() == fake_spk_kernel.epoch_jd


class TestSessionCap:
    def test_live_sessions_never_exceed_the_cap(self,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(target=session_manager, name="MAX_SESSIONS", value=3)
        for _ in range(10):
            session_manager.create_session()
        assert len(session_manager._sessions) == 3

    def test_the_least_recently_seen_session_is_evicted(self,
                                                        monkeypatch: pytest.MonkeyPatch
                                                        ) -> None:
        monkeypatch.setattr(target=session_manager, name="MAX_SESSIONS", value=3)
        first = session_manager.create_session()
        second = session_manager.create_session()
        third = session_manager.create_session()
        # `first` is the oldest by creation, but activity is what counts.
        session_manager.touch(first.session_id)

        fourth = session_manager.create_session()

        assert session_manager.get_session(second.session_id) is None
        for survivor in (first, third, fourth):
            assert session_manager.get_session(survivor.session_id) is not None

    def test_eviction_clears_the_last_seen_entry_too(self,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
        """`_last_seen` is the eviction key; a leaked entry would make the
        next eviction target an id that no longer exists."""
        monkeypatch.setattr(target=session_manager, name="MAX_SESSIONS", value=2)
        for _ in range(5):
            session_manager.create_session()
        assert set(session_manager._last_seen) == set(session_manager._sessions)


class TestIdleSweep:
    def test_idle_sessions_are_reaped_on_the_next_create(self,
                                                         monkeypatch: pytest.MonkeyPatch
                                                         ) -> None:
        monkeypatch.setattr(target=session_manager, name="MAX_IDLE_SECONDS", value=60.0)
        stale = session_manager.create_session()
        # Backdate past the idle window rather than sleeping through it.
        session_manager._last_seen[stale.session_id] -= 120.0

        session_manager.create_session()

        assert session_manager.get_session(stale.session_id) is None

    def test_touch_keeps_a_session_alive(self,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(target=session_manager, name="MAX_IDLE_SECONDS", value=60.0)
        kept = session_manager.create_session()
        session_manager._last_seen[kept.session_id] -= 120.0
        session_manager.touch(kept.session_id)

        session_manager.create_session()

        assert session_manager.get_session(kept.session_id) is not None

    def test_active_sessions_survive_the_sweep(self,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(target=session_manager, name="MAX_IDLE_SECONDS", value=60.0)
        active = session_manager.create_session()
        session_manager.create_session()
        assert session_manager.get_session(active.session_id) is not None
