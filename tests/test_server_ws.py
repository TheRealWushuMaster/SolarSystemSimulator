"""
The per-tick WebSocket: command dispatch, the flood throttle, and the
trail-delta protocol.

The throttle is driven by a fake clock rather than real sleeps, so the tests
state the timing they mean instead of racing it.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from config import simulation_steps
from core.trail import TrailPath
from core.vec3 import Vec3
from server import session_manager
from server import ws as ws_module
from server.session import SolaraSession


class FakeClock:
    """Stands in for the `time` module inside server.ws."""

    def __init__(self) -> None:
        self.now: float = 1000.0

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """Freeze ws.py's clock so every tick lands inside one throttle window."""
    clock = FakeClock()
    monkeypatch.setattr(target=ws_module, name="time", value=clock)
    return clock


def _new_session(api_client: TestClient) -> SolaraSession:
    session_id: str = api_client.post(url="/api/session").json()["session_id"]
    created = session_manager.get_session(session_id)
    assert created is not None
    return created


def _socket_url(session: SolaraSession) -> str:
    return f"/ws/session/{session.session_id}"


class TestConnection:
    def test_unknown_session_is_closed_with_4404(self, api_client: TestClient) -> None:
        with api_client.websocket_connect(url="/ws/session/nope") as socket:
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_json()
        assert closed.value.code == 4404

    def test_first_message_returns_full_state(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            state: dict[str, Any] = socket.receive_json()
        assert state["type"] == "state"
        assert "Earth" in state["bodies"]
        assert len(state["bodies"]["Earth"]["p"]) == 3
        assert state["hud"]["following"] == "Sun"
        assert state["plan"] == ["(parked -- no active flight)"]

    def test_a_message_refreshes_the_idle_timer(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        session_manager._last_seen[session.session_id] -= 600.0
        stale_at: float = session_manager._last_seen[session.session_id]
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            socket.receive_json()
        assert session_manager._last_seen[session.session_id] > stale_at

    def test_disconnect_leaves_the_session_alive(self, api_client: TestClient) -> None:
        """A backgrounded tab or a network blip must not destroy state -- the
        client reconnects to the same session id."""
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            socket.receive_json()
        assert session_manager.get_session(session.session_id) is session


class TestDispatch:
    def test_tick_does_not_advance_while_paused(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            state = socket.receive_json()
        assert state["sim_time_s"] == 0.0

    def test_tick_advances_by_one_time_step_while_playing(self,
                                                          api_client: TestClient) -> None:
        session = _new_session(api_client)
        session.set_play(playing=True)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            state = socket.receive_json()
        assert state["sim_time_s"] == session.time_step_s

    def test_tick_follows_the_play_direction(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        session.set_play(playing=True)
        session.reverse()
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            state = socket.receive_json()
        assert state["sim_time_s"] == -session.time_step_s

    def test_step_advances_even_while_paused(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "step", "direction": 1})
            state = socket.receive_json()
        assert state["sim_time_s"] == session.time_step_s

    def test_step_backwards(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "step", "direction": -1})
            state = socket.receive_json()
        assert state["sim_time_s"] == -session.time_step_s

    def test_set_play_is_reflected_in_the_hud(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "set_play", "playing": True})
            state = socket.receive_json()
        assert state["hud"]["playing"] is True
        assert session.auto_play is True

    def test_reverse_flips_the_hud_direction(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "reverse"})
            state = socket.receive_json()
        assert state["hud"]["direction"] == -1.0

    def test_set_time_step(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "set_time_step", "index": 2})
            state = socket.receive_json()
        assert state["hud"]["time_step_name"] == simulation_steps[2][0]

    def test_set_follow(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "set_follow", "target": "Mars"})
            state = socket.receive_json()
        assert state["hud"]["following"] == "Mars"

    def test_toggle_test_drive(self, api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "toggle_test_drive"})
            state = socket.receive_json()
        assert state["hud"]["test_drive"] is True

    def test_unknown_message_type_still_answers(self, api_client: TestClient) -> None:
        """A newer client talking to an older backend must not wedge the
        socket -- unknown types fall through the dispatch chain."""
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "warp_drive"})
            state = socket.receive_json()
        assert state["type"] == "state"
        assert state["sim_time_s"] == 0.0

    def test_malformed_message_without_a_type_still_answers(self,
                                                            api_client: TestClient) -> None:
        session = _new_session(api_client)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={})
            state = socket.receive_json()
        assert state["type"] == "state"


class TestTickThrottle:
    def test_over_rate_ticks_are_dropped(self,
                                         api_client: TestClient,
                                         frozen_clock: FakeClock) -> None:
        """Two ticks inside one throttle window advance the simulation once.

        The dropped tick produces no reply at all, so the second message read
        back is the answer to the `step` that follows it -- if the throttle
        had let the tick through, that read would see three steps of time.
        """
        session = _new_session(api_client)
        session.set_play(playing=True)
        step_s: float = session.time_step_s
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            first = socket.receive_json()
            socket.send_json(data={"type": "tick"})          # dropped
            socket.send_json(data={"type": "step", "direction": 1})
            second = socket.receive_json()

        assert first["sim_time_s"] == step_s
        assert second["sim_time_s"] == 2.0 * step_s

    def test_ticks_resume_after_the_interval(self,
                                             api_client: TestClient,
                                             frozen_clock: FakeClock) -> None:
        session = _new_session(api_client)
        session.set_play(playing=True)
        step_s: float = session.time_step_s
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            socket.send_json(data={"type": "tick"})
            socket.receive_json()
            frozen_clock.advance(seconds=ws_module.MIN_TICK_INTERVAL_S * 2.0)
            socket.send_json(data={"type": "tick"})
            second = socket.receive_json()

        assert second["sim_time_s"] == 2.0 * step_s

    def test_control_messages_are_never_throttled(self,
                                                  api_client: TestClient,
                                                  frozen_clock: FakeClock) -> None:
        """Only `tick` is rate-limited; a burst of UI commands in the same
        window must all take effect."""
        session = _new_session(api_client)
        step_s: float = session.time_step_s
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            for _ in range(3):
                socket.send_json(data={"type": "step", "direction": 1})
            states = [socket.receive_json() for _ in range(3)]

        assert [state["sim_time_s"] for state in states] == [step_s,
                                                             2.0 * step_s,
                                                             3.0 * step_s]

    def test_a_realistic_frame_rate_is_never_throttled(self,
                                                       api_client: TestClient,
                                                       frozen_clock: FakeClock) -> None:
        """The cap sits well above any real display, so a 60 Hz client must
        get every one of its ticks honoured."""
        session = _new_session(api_client)
        session.set_play(playing=True)
        step_s: float = session.time_step_s
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            for _ in range(5):
                socket.send_json(data={"type": "tick"})
                state = socket.receive_json()
                frozen_clock.advance(seconds=1.0 / 60.0)

        assert state["sim_time_s"] == 5.0 * step_s


class TestTrailProtocol:
    """
    The client keeps its own trail buffer and only ever receives deltas, so
    the socket has to tell it when to throw that buffer away. A shrinking
    trail means the session swapped in a fresh TrailPath (set_home,
    load_mission, or a launched mission) and the client must re-seed.
    """

    @staticmethod
    def _seed_trail(session: SolaraSession, count: int) -> None:
        # The session is parked (no sim_ship), so `advance` never touches the
        # trail -- these points stay exactly as written.
        session.trail.points = [Vec3(float(index), 0.0, 0.0) for index in range(count)]

    @staticmethod
    def _tick(socket: Any, clock: FakeClock) -> dict[str, Any]:
        """Send one tick and read its state.

        The clock is stepped past the throttle window first: consecutive ticks
        from a test arrive far faster than any real client's frame rate, and a
        throttled tick is dropped *without a reply*, which would block the
        read forever.
        """
        clock.advance(seconds=ws_module.MIN_TICK_INTERVAL_S * 2.0)
        socket.send_json(data={"type": "tick"})
        return socket.receive_json()

    def test_first_message_sends_the_whole_trail(self,
                                                 api_client: TestClient,
                                                 frozen_clock: FakeClock) -> None:
        session = _new_session(api_client)
        self._seed_trail(session, count=3)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            state = self._tick(socket, frozen_clock)
        assert state["ship"]["trail_reset"] is False
        assert len(state["ship"]["trail_append"]) == 3

    def test_only_new_points_are_sent(self,
                                      api_client: TestClient,
                                      frozen_clock: FakeClock) -> None:
        session = _new_session(api_client)
        self._seed_trail(session, count=3)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            self._tick(socket, frozen_clock)
            session.trail.points.append(Vec3(99.0, 0.0, 0.0))
            state = self._tick(socket, frozen_clock)
        assert state["ship"]["trail_append"] == [[99.0, 0.0, 0.0]]
        assert state["ship"]["trail_reset"] is False

    def test_an_unchanged_trail_sends_nothing(self,
                                              api_client: TestClient,
                                              frozen_clock: FakeClock) -> None:
        session = _new_session(api_client)
        self._seed_trail(session, count=3)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            self._tick(socket, frozen_clock)
            state = self._tick(socket, frozen_clock)
        assert state["ship"]["trail_append"] == []

    def test_a_replaced_trail_asks_the_client_to_reset(self,
                                                       api_client: TestClient,
                                                       frozen_clock: FakeClock) -> None:
        session = _new_session(api_client)
        self._seed_trail(session, count=5)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            self._tick(socket, frozen_clock)
            # What set_home/load_mission do: a brand new, near-empty path.
            session.trail = TrailPath(min_separation_km=1.0e6, max_points=4000)
            session.trail.points = [Vec3(7.0, 0.0, 0.0)]
            state = self._tick(socket, frozen_clock)

        assert state["ship"]["trail_reset"] is True
        assert state["ship"]["trail_append"] == [[7.0, 0.0, 0.0]]

    def test_appending_resumes_after_a_reset(self,
                                             api_client: TestClient,
                                             frozen_clock: FakeClock) -> None:
        """The retained length must be re-based on the new trail, or every
        later message would keep re-sending it."""
        session = _new_session(api_client)
        self._seed_trail(session, count=5)
        with api_client.websocket_connect(url=_socket_url(session)) as socket:
            self._tick(socket, frozen_clock)
            session.trail = TrailPath(min_separation_km=1.0e6, max_points=4000)
            session.trail.points = [Vec3(7.0, 0.0, 0.0)]
            self._tick(socket, frozen_clock)
            session.trail.points.append(Vec3(8.0, 0.0, 0.0))
            state = self._tick(socket, frozen_clock)

        assert state["ship"]["trail_reset"] is False
        assert state["ship"]["trail_append"] == [[8.0, 0.0, 0.0]]
