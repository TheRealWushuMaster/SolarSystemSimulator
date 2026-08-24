"""
Behaviour of `SolaraSession` -- the per-browser-tab simulation state.

Everything here runs against `tests.fake_kernel`, so the real ephemeris is
never needed. The Lambert-backed paths (`fly_to`'s planning branch, the Moon
trip) depend on genuine orbital geometry and are covered by the core/ suite
instead; what is tested here is the session's own bookkeeping -- command
handling, mission/trail lifecycle, and the export guard rails.
"""

from __future__ import annotations

import os
from datetime import timedelta

import pytest

from config import simulation_steps
from core.vec3 import Vec3
from server import session
from server.session import PARKING_ALTITUDE_KM, SolaraSession
from tests.fake_kernel import FakeSpkKernel

VOYAGER_1: str = "Voyager 1"


class TestConstruction:
    def test_loads_every_body_from_json(self, session: SolaraSession) -> None:
        assert "Sun" in session.bodies
        assert "Earth" in session.bodies
        assert "Moon" in session.bodies

    def test_bodies_are_synced_to_the_initial_time(self, session: SolaraSession) -> None:
        """Construction ends with a _sync_bodies_to_time, so nothing is at the
        origin with a zero velocity (which is what an unsynced body looks like)."""
        earth = session.bodies["Earth"]
        assert earth.position.magnitude() > 0.0
        assert earth.velocity.magnitude() > 0.0

    def test_sessions_do_not_share_body_objects(self,
                                                fake_spk_kernel: FakeSpkKernel) -> None:
        """Bodies are mutated every tick, so two tabs must not alias them."""
        first = SolaraSession(kernel=fake_spk_kernel)
        second = SolaraSession(kernel=fake_spk_kernel)
        assert first.bodies["Earth"] is not second.bodies["Earth"]
        first.advance(dt_s=86400.0)
        assert first.bodies["Earth"].position != second.bodies["Earth"].position

    def test_session_ids_are_unique(self, fake_spk_kernel: FakeSpkKernel) -> None:
        first = SolaraSession(kernel=fake_spk_kernel)
        second = SolaraSession(kernel=fake_spk_kernel)
        assert first.session_id != second.session_id

    def test_starts_parked_around_earth(self, session: SolaraSession) -> None:
        assert session.parked is True
        assert session.home_body == "Earth"
        assert session.sim_ship is None

    def test_epoch_is_loaded_per_session_not_shared(self,
                                                    fake_spk_kernel: FakeSpkKernel) -> None:
        """A regression guard: the session must derive its own "now" rather
        than accept a server-boot epoch, or the displayed date drifts out of
        sync with the body positions as server uptime grows."""
        built = SolaraSession(kernel=fake_spk_kernel)
        # The ephemeris epoch is the session's own epoch, not the kernel's.
        assert built.ephemeris.epoch_jd != fake_spk_kernel.epoch_jd


class TestSimulationTime:
    def test_current_date_tracks_sim_time(self, session: SolaraSession) -> None:
        start = session.current_date
        session.advance(dt_s=3600.0)
        assert session.current_date - start == timedelta(seconds=3600)

    def test_advance_backwards(self, session: SolaraSession) -> None:
        start = session.current_date
        session.advance(dt_s=-3600.0)
        assert session.current_date < start

    def test_advance_resyncs_bodies(self, session: SolaraSession) -> None:
        before = session.bodies["Earth"].position
        session.advance(dt_s=86400.0)
        assert session.bodies["Earth"].position != before

    def test_time_step_properties_follow_the_index(self, session: SolaraSession) -> None:
        session.set_time_step(index=0)
        assert session.time_step_name == simulation_steps[0][0]
        assert session.time_step_s == float(simulation_steps[0][1])


class TestCommands:
    def test_set_play(self, session: SolaraSession) -> None:
        session.set_play(playing=True)
        assert session.auto_play is True
        session.set_play(playing=False)
        assert session.auto_play is False

    def test_reverse_flips_direction(self, session: SolaraSession) -> None:
        assert session.play_direction == 1.0
        session.reverse()
        assert session.play_direction == -1.0
        session.reverse()
        assert session.play_direction == 1.0

    def test_toggle_test_drive_returns_new_state(self, session: SolaraSession) -> None:
        assert session.toggle_test_drive() is True
        assert session.use_test_ship is True
        assert session.toggle_test_drive() is False

    @pytest.mark.parametrize("index", [-5, len(simulation_steps) + 5])
    def test_set_time_step_clamps_out_of_range(self,
                                               session: SolaraSession,
                                               index: int) -> None:
        session.set_time_step(index=index)
        assert 0 <= session.time_step_index < len(simulation_steps)

    def test_set_follow_accepts_a_body(self, session: SolaraSession) -> None:
        session.set_follow(target="Mars")
        assert session.follow_target == "Mars"

    def test_set_follow_accepts_the_ship(self, session: SolaraSession) -> None:
        session.set_follow(target="Ship")
        assert session.follow_target == "Ship"

    def test_set_follow_ignores_unknown_target(self, session: SolaraSession) -> None:
        session.set_follow(target="Mars")
        session.set_follow(target="Vulcan")
        assert session.follow_target == "Mars"


class TestSetHome:
    def test_rejects_unknown_body(self, session: SolaraSession) -> None:
        assert session.set_home(body="Vulcan") is False
        assert session.home_body == "Earth"

    def test_moves_home_and_follows_it(self, session: SolaraSession) -> None:
        assert session.set_home(body="Mars") is True
        assert session.home_body == "Mars"
        assert session.follow_target == "Mars"

    def test_ends_any_active_mission(self, session: SolaraSession) -> None:
        session.load_mission(name=VOYAGER_1)
        assert session.sim_ship is not None
        session.set_home(body="Mars")
        assert session.sim_ship is None
        assert session.parked is True
        assert session.historical_active is False
        assert session.mission_label == ""

    def test_replaces_the_trail(self, session: SolaraSession) -> None:
        """The client detects a shrinking trail and re-seeds; set_home must
        therefore hand it a genuinely fresh TrailPath, not a cleared one."""
        session.load_mission(name=VOYAGER_1)
        old_trail = session.trail
        session.set_home(body="Mars")
        assert session.trail is not old_trail
        assert len(session.trail.points) == 0


class TestParkedShip:
    def test_parked_ship_orbits_the_home_body(self, session: SolaraSession) -> None:
        earth = session.bodies["Earth"]
        offset: Vec3 = session.ship_position() - earth.position
        assert offset.magnitude() == pytest.approx(earth.radius + PARKING_ALTITUDE_KM)

    def test_parked_ship_tracks_the_home_body_over_time(self,
                                                        session: SolaraSession) -> None:
        session.advance(dt_s=86400.0)
        earth = session.bodies["Earth"]
        offset: Vec3 = session.ship_position() - earth.position
        assert offset.magnitude() == pytest.approx(earth.radius + PARKING_ALTITUDE_KM)

    def test_parked_ship_has_no_velocity(self, session: SolaraSession) -> None:
        assert session.ship_velocity() == Vec3()

    def test_parking_orbit_follows_the_new_home(self, session: SolaraSession) -> None:
        session.set_home(body="Jupiter")
        jupiter = session.bodies["Jupiter"]
        offset: Vec3 = session.ship_position() - jupiter.position
        assert offset.magnitude() == pytest.approx(jupiter.radius + PARKING_ALTITUDE_KM)


class TestFlyToGuards:
    def test_rejects_the_home_body(self, session: SolaraSession) -> None:
        assert session.fly_to(target="Earth") == {"status": "invalid_target"}

    def test_rejects_unknown_body(self, session: SolaraSession) -> None:
        assert session.fly_to(target="Vulcan") == {"status": "invalid_target"}

    def test_rejects_empty_target(self, session: SolaraSession) -> None:
        """The route passes `str(body.get("target", ""))`, so an absent field
        arrives here as an empty string rather than being rejected earlier."""
        assert session.fly_to(target="") == {"status": "invalid_target"}

    def test_a_rejected_target_leaves_the_session_parked(self,
                                                         session: SolaraSession) -> None:
        session.fly_to(target="Vulcan")
        assert session.parked is True
        assert session.mission_active is False


class TestLoadMission:
    def test_unknown_mission(self, session: SolaraSession) -> None:
        assert session.load_mission(name="Apollo 13") == {"status": "unknown_mission"}

    def test_loads_a_historical_mission(self, session: SolaraSession) -> None:
        result = session.load_mission(name=VOYAGER_1)
        assert result["status"] == "ok"
        assert VOYAGER_1 in result["mission_label"]
        assert session.historical_active is True
        assert session.mission_active is False
        assert session.parked is False
        assert session.sim_ship is not None

    def test_jumps_to_the_mission_epoch(self, session: SolaraSession) -> None:
        """sim_time_s is the offset from the session's own epoch to the
        mission's launch-era state vector -- Voyager 1 launched in 1977, well
        before any session's "now", so the offset must be negative."""
        session.load_mission(name=VOYAGER_1)
        assert session.sim_time_s < 0.0
        assert session.current_date.year == 1977

    def test_seeds_the_trail_with_the_start_position(self,
                                                     session: SolaraSession) -> None:
        session.load_mission(name=VOYAGER_1)
        assert len(session.trail.points) == 1

    def test_stops_autoplay_so_the_user_starts_the_flight(self,
                                                          session: SolaraSession) -> None:
        session.set_play(playing=True)
        session.load_mission(name=VOYAGER_1)
        assert session.auto_play is False

    def test_switching_missions_replaces_the_trail(self,
                                                   session: SolaraSession) -> None:
        session.load_mission(name=VOYAGER_1)
        session.advance(dt_s=86400.0)
        old_trail = session.trail
        session.load_mission(name="Voyager 2")
        assert session.trail is not old_trail
        assert len(session.trail.points) == 1


class TestExport:
    @pytest.fixture(autouse=True)
    def export_dir(self,
                   monkeypatch: pytest.MonkeyPatch,
                   tmp_path: object) -> str:
        """Redirect exports to a temp dir -- these tests delete files."""
        directory = str(tmp_path)
        monkeypatch.setattr(target=session, name="EXPORT_DIR", value=directory)
        return directory

    def test_export_while_parked_is_rejected(self, session: SolaraSession) -> None:
        result = session.export_trajectory()
        assert result["status"] == "empty"

    def test_export_before_flying_is_rejected(self, session: SolaraSession) -> None:
        """A freshly loaded mission has exactly one history snapshot; there is
        no trajectory to export until it has actually been stepped."""
        session.load_mission(name=VOYAGER_1)
        assert session.export_trajectory()["status"] == "empty"

    def test_export_writes_a_csv(self,
                                 session: SolaraSession,
                                 export_dir: str) -> None:
        session.load_mission(name=VOYAGER_1)
        session.advance(dt_s=86400.0)
        result = session.export_trajectory()
        assert result["status"] == "ok"
        assert result["rows"] >= 2
        assert os.path.isfile(result["path"])
        assert os.path.dirname(result["path"]) == export_dir

    def test_export_filename_has_no_spaces(self,
                                           session: SolaraSession) -> None:
        """The filename is served straight back over HTTP, and the mission
        names in data/missions.json contain spaces."""
        session.load_mission(name=VOYAGER_1)
        session.advance(dt_s=86400.0)
        result = session.export_trajectory()
        assert " " not in os.path.basename(result["path"])


class TestExportRetention:
    def test_sweep_keeps_the_newest_files(self,
                                          monkeypatch: pytest.MonkeyPatch,
                                          tmp_path: object) -> None:
        directory = str(tmp_path)
        monkeypatch.setattr(target=session, name="EXPORT_DIR", value=directory)
        monkeypatch.setattr(target=session, name="EXPORT_MAX_FILES", value=3)
        for index in range(6):
            path = os.path.join(directory, f"export_{index}.csv")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("x")
            # Explicit mtimes -- files written this fast can share a timestamp.
            os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))

        session._sweep_exports()

        remaining = sorted(os.listdir(directory))
        assert remaining == ["export_3.csv", "export_4.csv", "export_5.csv"]

    def test_sweep_is_a_no_op_below_the_cap(self,
                                            monkeypatch: pytest.MonkeyPatch,
                                            tmp_path: object) -> None:
        directory = str(tmp_path)
        monkeypatch.setattr(target=session, name="EXPORT_DIR", value=directory)
        monkeypatch.setattr(target=session, name="EXPORT_MAX_FILES", value=3)
        for index in range(2):
            with open(os.path.join(directory, f"export_{index}.csv"), "w",
                      encoding="utf-8") as handle:
                handle.write("x")

        session._sweep_exports()

        assert len(os.listdir(directory)) == 2
