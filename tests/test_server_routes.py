"""
The REST surface: static catalogues, session lifecycle, and the one-shot
mission menu actions.

These go through the real router via `TestClient` (see `api_client` in
conftest), so route wiring, status codes and response shapes are all
covered -- only the SPK kernel behind them is faked.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config import ORBIT_SAMPLES
from server import session as session_module
from server import session_manager

VOYAGER_1: str = "Voyager 1"


def _new_session_id(client: TestClient) -> str:
    response = client.post(url="/api/session")
    assert response.status_code == 200
    return response.json()["session_id"]


class TestCatalogues:
    def test_bodies_lists_every_body(self, api_client: TestClient) -> None:
        catalogue = api_client.get(url="/api/bodies").json()
        assert {"Sun", "Earth", "Moon", "Pluto"} <= set(catalogue)

    def test_body_entry_has_the_wire_shape(self, api_client: TestClient) -> None:
        earth = api_client.get(url="/api/bodies").json()["Earth"]
        assert earth["radius_km"] > 0.0
        assert earth["mass_kg"] > 0.0
        assert earth["parent_body"] == "Sun"
        assert earth["is_star"] is False

    def test_the_sun_is_flagged_as_a_star(self, api_client: TestClient) -> None:
        assert api_client.get(url="/api/bodies").json()["Sun"]["is_star"] is True

    def test_missions_lists_the_catalogue(self, api_client: TestClient) -> None:
        missions = api_client.get(url="/api/missions").json()
        assert VOYAGER_1 in missions
        assert missions[VOYAGER_1]["description"]

    def test_orbit_lines_cover_the_sun_orbiting_bodies(self,
                                                       api_client: TestClient) -> None:
        lines = api_client.get(url="/api/orbit_lines").json()
        assert "Earth" in lines
        # The Moon orbits Earth, not the Sun, so it gets no heliocentric line.
        assert "Moon" not in lines
        assert "Sun" not in lines

    def test_orbit_lines_are_sampled_over_one_period(self,
                                                     api_client: TestClient) -> None:
        lines = api_client.get(url="/api/orbit_lines").json()
        assert len(lines["Earth"]) == ORBIT_SAMPLES + 1
        assert len(lines["Earth"][0]) == 3

    def test_catalogues_need_no_session(self, api_client: TestClient) -> None:
        """They are static and unauthenticated -- the frontend fetches them
        before it has a session id."""
        for path in ("/api/bodies", "/api/missions", "/api/orbit_lines"):
            assert api_client.get(url=path).status_code == 200


class TestSessionLifecycle:
    def test_create_returns_a_registered_session(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        assert session_manager.get_session(session_id) is not None

    def test_each_create_is_a_distinct_session(self, api_client: TestClient) -> None:
        assert _new_session_id(api_client) != _new_session_id(api_client)

    def test_delete_drops_the_session(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        assert api_client.delete(url=f"/api/session/{session_id}").status_code == 200
        assert session_manager.get_session(session_id) is None

    def test_delete_unknown_session_is_404(self, api_client: TestClient) -> None:
        assert api_client.delete(url="/api/session/nope").status_code == 404

    def test_a_command_refreshes_the_idle_timer(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        session_manager._last_seen[session_id] -= 600.0
        stale_at: float = session_manager._last_seen[session_id]

        api_client.post(url=f"/api/session/{session_id}/set_home",
                        json={"body": "Mars"})

        assert session_manager._last_seen[session_id] > stale_at


class TestUnknownSession:
    """Every session-scoped route must 404 rather than 500 on a stale id --
    the frontend holds session ids across reconnects and server restarts."""

    @pytest.mark.parametrize(("path", "payload"), [
        ("set_home", {"body": "Mars"}),
        ("fly_to", {"target": "Mars"}),
        ("load_mission", {"name": VOYAGER_1}),
        ("export", {}),
    ])
    def test_post_routes_404(self,
                             api_client: TestClient,
                             path: str,
                             payload: dict[str, str]) -> None:
        response = api_client.post(url=f"/api/session/missing/{path}",
                                   json=payload)
        assert response.status_code == 404


class TestSetHome:
    def test_sets_the_home_body(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/set_home",
                                   json={"body": "Mars"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "home_body": "Mars"}

    def test_unknown_body_is_400(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/set_home",
                                   json={"body": "Vulcan"})
        assert response.status_code == 400

    def test_missing_field_is_400(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/set_home",
                                   json={})
        assert response.status_code == 400


class TestFlyTo:
    def test_invalid_target_reports_status_in_the_body(self,
                                                       api_client: TestClient) -> None:
        """fly_to answers 200 with a status field rather than an HTTP error --
        the frontend shows it as a HUD notification."""
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/fly_to",
                                   json={"target": "Vulcan"})
        assert response.status_code == 200
        assert response.json() == {"status": "invalid_target"}

    def test_missing_target_is_invalid(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/fly_to",
                                   json={})
        assert response.json() == {"status": "invalid_target"}


class TestLoadMission:
    def test_loads_a_historical_mission(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/load_mission",
                                   json={"name": VOYAGER_1})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_unknown_mission_is_400(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/load_mission",
                                   json={"name": "Apollo 13"})
        assert response.status_code == 400


class TestExport:
    @pytest.fixture(autouse=True)
    def export_dir(self,
                   monkeypatch: pytest.MonkeyPatch,
                   tmp_path: object) -> None:
        monkeypatch.setattr(target=session_module,
                            name="EXPORT_DIR",
                            value=str(tmp_path))

    def test_nothing_to_export_is_400(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        response = api_client.post(url=f"/api/session/{session_id}/export")
        assert response.status_code == 400

    def test_export_returns_csv(self, api_client: TestClient) -> None:
        session_id = _new_session_id(api_client)
        api_client.post(url=f"/api/session/{session_id}/load_mission",
                        json={"name": VOYAGER_1})
        session = session_manager.get_session(session_id)
        assert session is not None
        session.advance(dt_s=86400.0)

        response = api_client.post(url=f"/api/session/{session_id}/export")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        header_line: str = response.text.splitlines()[0]
        assert header_line.startswith("time_s,x_km,y_km,z_km")
        assert len(response.text.splitlines()) >= 3   # header + two states
