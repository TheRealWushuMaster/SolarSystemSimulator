"""
Per-connection simulation state -- the non-Ursina slice of app.py's SolaraApp.

Phase 3 adds missions: FLY_TO Lambert transfers, historical spacecraft
replay, and the custom Earth-Moon-Earth round trip. Ported near-verbatim
from app.py's advance()/_advance_mission()/_advance_historical()/_fly_to()/
_load_mission()/_load_moon_mission(), minus every Ursina/camera/HUD call.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from math import cos, pi, sin, sqrt
from typing import Any

from core.bodies import CelestialBody
from core.ephemeris import JplEphemeris
from core.export import export_csv
from core.flight_plan import FlightPlan
from core.lambert import MU_SUN, LambertNoConvergence, solve_lambert
from core.mission_planner import MissionPlanner, Objective
from core.missions import HistoricalMission, load_missions
from core.moon_transfer import MoonMissionState, plan_moon_transfer
from core.physics import G, circular_orbit_velocity
from core.propagator import DEFAULT_DT_MAX, advance_coasting
from core.spaceship import PropulsionSystem, Spaceship
from core.trail import TrailPath
from core.bodies import load_bodies_from_json
from core.vec3 import Vec3
from config import simulation_steps

DEFAULT_TIME_STEP_INDEX: int = 7  # "1 day", matches app.py's default
MOON_TRIP_NAME: str = "Earth-Moon trip"
MOON_PARKING_ALTITUDE_KM: float = 500.0
PARKING_ALTITUDE_KM: float = 2000.0
INSERTION_ALTITUDE_KM: float = 500.0
MISSION_SHIP_MAX_DT: float = 300.0
MCC_FRACTIONS: tuple[float, ...] = (0.5, 0.8, 0.93)
MIN_MCC_LEAD_S: float = 3.0 * 86400.0
INTERPLANETARY_TRAIL_KM: float = 2.0e6
MOON_TRAIL_KM: float = 5000.0
MISSIONS_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                  "data", "missions.json")
EXPORT_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exports")


class SolaraSession:
    """
    One browser tab's worth of simulation state. Never shared across
    sessions: `bodies` is a fresh dict built from data/bodies.json at
    construction time (CelestialBody instances are mutated every tick by
    `_sync_bodies_to_time`), and `ephemeris` wraps the one shared, read-only
    SPK kernel in its own lightweight JplEphemeris instance.
    """

    def __init__(self, kernel: Any, epoch_jd: float) -> None:
        self.session_id: str = uuid.uuid4().hex
        self.epoch: datetime = datetime.now()
        self.bodies: dict[str, CelestialBody] = load_bodies_from_json()
        self.ephemeris: JplEphemeris = JplEphemeris.from_bodies(
            kernel=kernel, bodies=self.bodies, epoch_jd=epoch_jd)

        self.sim_time_s: float = 0.0
        self.time_step_index: int = DEFAULT_TIME_STEP_INDEX
        self.auto_play: bool = False
        self.play_direction: float = 1.0
        self.follow_target: str = "Sun"
        self.home_body: str = "Earth"
        self.use_test_ship: bool = False

        self.planner: MissionPlanner = MissionPlanner(ephemeris=self.ephemeris, mu=MU_SUN)
        self.missions: dict[str, HistoricalMission] = load_missions(MISSIONS_FILE)
        self.mission_label: str = ""
        self.last_notification: str = ""

        # The craft always exists conceptually: while idle (`parked`) it
        # rides a kinematic circular parking orbit around `home_body`; a
        # mission replaces it with a real, simulated `sim_ship`.
        self.parked: bool = True
        self.sim_ship: Spaceship | None = None
        self.trail: TrailPath = TrailPath(min_separation_km=INTERPLANETARY_TRAIL_KM,
                                          max_points=4000)

        self.mission_active: bool = False
        self.historical_active: bool = False
        self.moon_trip: bool = False
        self.moon_state: MoonMissionState | None = None
        self.mission_target: str = ""
        self.mission_departure_time: float = 0.0
        self.mission_arrival_time: float = 0.0
        self.mission_capture_km: float = 0.0
        self.mission_insertion_budget: float = 6.0
        self.mission_insertion_altitude: float = INSERTION_ALTITUDE_KM
        self.mission_gravity_bodies: dict[str, CelestialBody] = {}
        self.mcc_index: int = 0

        self._sync_bodies_to_time(self.sim_time_s)

    # ------------------------------------------------------------------
    # Simulation time (mirrors SolaraApp's properties)
    # ------------------------------------------------------------------

    @property
    def time_step_s(self) -> float:
        return float(simulation_steps[self.time_step_index][1])

    @property
    def time_step_name(self) -> str:
        return simulation_steps[self.time_step_index][0]

    @property
    def current_date(self) -> datetime:
        return self.epoch + timedelta(seconds=self.sim_time_s)

    def _sync_bodies_to_time(self, time_s: float) -> None:
        for name, body in self.bodies.items():
            position, velocity = self.ephemeris.state(name, time_s)
            body.position = position
            body.velocity = velocity

    # ------------------------------------------------------------------
    # Ship position (parked kinematic orbit, or the simulated craft)
    # ------------------------------------------------------------------

    def ship_position(self) -> Vec3:
        return self._parking_position() if self.parked else self.sim_ship.position

    def ship_velocity(self) -> Vec3:
        if self.parked:
            return Vec3()
        return self.sim_ship.velocity

    def _parking_position(self) -> Vec3:
        """Kinematic circular parking orbit around the home body, computed
        directly from its live position so it tracks the planet exactly at
        any time step (mirrors app.py's _parking_position)."""
        body = self.bodies[self.home_body]
        orbit_radius: float = body.radius + PARKING_ALTITUDE_KM
        angular_rate: float = circular_orbit_velocity(body.mass, orbit_radius) / orbit_radius
        angle: float = angular_rate * self.sim_time_s
        offset = Vec3(orbit_radius * cos(angle), orbit_radius * sin(angle), 0.0)
        return body.position + offset

    # ------------------------------------------------------------------
    # Advance
    # ------------------------------------------------------------------

    def advance(self, dt_s: float) -> None:
        if self.mission_active and not self.parked and dt_s > 0.0 and self.sim_ship is not None:
            self._advance_mission(dt_s)
        elif self.historical_active and dt_s > 0.0 and self.sim_ship is not None:
            self._advance_historical(dt_s)
        else:
            self.sim_time_s += dt_s
            self._sync_bodies_to_time(self.sim_time_s)
        if self.moon_trip and self.moon_state is not None and self.sim_ship is not None:
            self.moon_state.step(self.sim_ship, self.bodies["Earth"], self.sim_time_s)
        if self.sim_ship is not None and self.trail.add(self.sim_ship.position):
            pass  # the delta is picked up by serialization from trail.points

    def _advance_historical(self, dt_s: float) -> None:
        """Coast a real craft forward under full N-body gravity (adaptive)."""
        advance_coasting(self.sim_ship, self.ephemeris, self.bodies, self.sim_time_s, dt_s)
        self.sim_time_s += dt_s
        self._sync_bodies_to_time(self.sim_time_s)

    def _advance_mission(self, dt_s: float) -> None:
        fine_chunk: float = self.sim_ship.max_integration_dt
        remaining: float = dt_s
        while remaining > 1e-6:
            target = self.bodies[self.mission_target]
            distance: float = (self.sim_ship.position - target.position).magnitude()
            cap: float = self.mission_capture_km
            if distance <= 4.0 * cap:
                chunk = fine_chunk
            elif distance <= 20.0 * cap:
                chunk = 3600.0
            else:
                chunk = 86400.0
            step: float = min(chunk, remaining)
            self.sim_time_s += step
            for name, body in self.mission_gravity_bodies.items():
                position, velocity = self.ephemeris.state(name, self.sim_time_s)
                body.position = position
                body.velocity = velocity
            self.sim_ship.step_forward(step, self.mission_gravity_bodies)
            self._maybe_correct_course()
            remaining -= step
        self._sync_bodies_to_time(self.sim_time_s)

    def _maybe_correct_course(self) -> None:
        """Re-solve Lambert from the live state and burn the correction at
        scheduled mid-course-correction fractions of the transfer."""
        if (not self.mission_active or self.sim_ship is None
                or self.mcc_index >= len(MCC_FRACTIONS)):
            return
        total: float = self.mission_arrival_time - self.mission_departure_time
        remaining: float = self.mission_arrival_time - self.sim_time_s
        if total <= 0.0:
            return
        progress: float = 1.0 - remaining / total
        if progress < MCC_FRACTIONS[self.mcc_index]:
            return
        self.mcc_index += 1

        if remaining < MIN_MCC_LEAD_S:
            return
        target_position = self.ephemeris.state(self.mission_target, self.mission_arrival_time)[0]
        if (self.sim_ship.position - self.bodies[self.mission_target].position
                ).magnitude() < self.mission_capture_km:
            return
        try:
            lambert = solve_lambert(r1=self.sim_ship.position, r2=target_position,
                                    time_of_flight=remaining, mu=MU_SUN)
        except LambertNoConvergence:
            return
        correction: Vec3 = lambert.v1 - self.sim_ship.velocity
        if correction.magnitude() < 1.0e-4:
            return
        self.sim_ship.flight_plan = (
            FlightPlan()
            .add_delta_v_vector(delta_v_vector_km_s=correction, duration=600.0)
            .add_orbit_insertion(body=self.mission_target,
                                 target_altitude_km=self.mission_insertion_altitude,
                                 capture_radius_km=self.mission_capture_km,
                                 max_delta_v_km_s=self.mission_insertion_budget))

    # ------------------------------------------------------------------
    # FLY_TO missions
    # ------------------------------------------------------------------

    def _make_mission_ship(self, position: Vec3, velocity: Vec3, plan: FlightPlan) -> Spaceship:
        if self.use_test_ship:
            engine = PropulsionSystem(max_thrust=3.0e6, reactionless=True)
        else:
            engine = PropulsionSystem(max_thrust=3.0e6, specific_impulse=450.0,
                                      exhaust_velocity=4500.0, fuel_mass=1.2e5)
        return Spaceship(structure_mass=4000.0, payload_mass=1000.0,
                         main_propulsion=engine,
                         initial_position=position, initial_velocity=velocity,
                         flight_plan=plan, max_integration_dt=MISSION_SHIP_MAX_DT)

    def fly_to(self, target: str) -> dict[str, Any]:
        """Plan the cheapest transfer to `target` and launch the mission."""
        if target == self.home_body or target not in self.bodies:
            return {"status": "invalid_target"}
        origin = self.home_body
        try:
            departures, flights = self.planner.transfer_grid(origin, target, self.sim_time_s,
                                                              self.bodies)
            solution = self.planner.plan_transfer(origin=origin, target=target,
                                                  departure_times=departures,
                                                  flight_times=flights,
                                                  objective=Objective.MIN_DELTA_V)
        except LambertNoConvergence:
            return {"status": "no_window", "message": f"no {origin}->{target} window found"}

        capture_km = self.planner.capture_radius(target, self.sim_time_s, self.bodies)
        insertion_altitude = max(INSERTION_ALTITUDE_KM,
                                 0.15 * capture_km - self.bodies[target].radius)
        insertion_budget = 3.0 * solution.arrival_delta_v.magnitude() + 2.0
        plan = self.planner.to_flight_plan(solution, burn_duration=600.0, orbit_insertion=True,
                                           insertion_altitude_km=insertion_altitude,
                                           capture_radius_km=capture_km,
                                           insertion_max_delta_v_km_s=insertion_budget)
        self._launch_mission(solution, plan, capture_km, insertion_budget, insertion_altitude)
        return {"status": "ok", "mission_label": self.mission_label}

    def _launch_mission(self, solution, plan: FlightPlan, capture_km: float,
                        insertion_budget: float, insertion_altitude: float) -> None:
        self.sim_time_s = solution.departure_time
        self._sync_bodies_to_time(self.sim_time_s)
        position, velocity = self.ephemeris.state(solution.origin, solution.departure_time)
        self.sim_ship = self._make_mission_ship(position, velocity, plan)
        self.parked = False

        self.trail = TrailPath(min_separation_km=INTERPLANETARY_TRAIL_KM, max_points=4000)
        self.trail.add(self.sim_ship.position)

        self.mission_active = True
        self.historical_active = False
        self.moon_trip = False
        self.moon_state = None
        self.mission_target = solution.target
        self.mission_departure_time = solution.departure_time
        self.mission_arrival_time = solution.arrival_time
        self.mission_capture_km = capture_km
        self.mission_insertion_budget = insertion_budget
        self.mission_insertion_altitude = insertion_altitude
        self.mission_gravity_bodies = {"Sun": self.bodies["Sun"],
                                       solution.target: self.bodies[solution.target]}
        self.mcc_index = 0

        self.auto_play = False
        self.mission_label = (f"{solution.origin} -> {solution.target}  "
                              f"dv {solution.total_delta_v:.2f} km/s  "
                              f"tof {solution.time_of_flight / 86400.0:.0f} d  "
                              f"(press space)")

    # ------------------------------------------------------------------
    # Historical missions and the Moon trip
    # ------------------------------------------------------------------

    def _make_historical_ship(self, mission: HistoricalMission) -> Spaceship:
        return Spaceship(structure_mass=mission.structure_mass, payload_mass=0.0,
                         main_propulsion=PropulsionSystem(),
                         initial_position=mission.position, initial_velocity=mission.velocity,
                         flight_plan=FlightPlan(), max_integration_dt=DEFAULT_DT_MAX)

    def load_mission(self, name: str) -> dict[str, Any]:
        if name == MOON_TRIP_NAME:
            self._load_moon_mission()
            return {"status": "ok", "mission_label": self.mission_label}
        if name not in self.missions:
            return {"status": "unknown_mission"}
        mission = self.missions[name]
        self.sim_time_s = (mission.epoch_jd - self.ephemeris.epoch_jd) * 86400.0
        self._sync_bodies_to_time(self.sim_time_s)

        self.sim_ship = self._make_historical_ship(mission)
        self.parked = False
        self.mission_active = False
        self.historical_active = True
        self.moon_trip = False
        self.moon_state = None
        self.mission_target = name
        self.mission_departure_time = self.sim_time_s

        self.trail = TrailPath(min_separation_km=INTERPLANETARY_TRAIL_KM, max_points=4000)
        self.trail.add(self.sim_ship.position)

        if mission.follow in self.bodies:
            self.follow_target = mission.follow
        self.auto_play = False
        self.mission_label = f"{name}: {mission.description}"
        self.last_notification = f"{name} loaded at {self.current_date:%Y-%m-%d}. Press space to fly."
        return {"status": "ok", "mission_label": self.mission_label}

    def _load_moon_mission(self) -> None:
        """A made-up Earth->Moon->Earth trip: a Hohmann transfer out, a free
        return burn at the Moon, and event-based circularization back home."""
        self.sim_time_s = 0.0
        self._sync_bodies_to_time(self.sim_time_s)
        earth = self.bodies["Earth"]
        moon = self.bodies["Moon"]

        plan_result = plan_moon_transfer(earth, moon, self.ephemeris, self.sim_time_s,
                                         parking_altitude_km=MOON_PARKING_ALTITUDE_KM)
        flight_plan = FlightPlan().add_coast(duration=2.2 * plan_result.time_of_flight)

        self.sim_ship = Spaceship(
            structure_mass=5000.0, payload_mass=0.0,
            main_propulsion=PropulsionSystem(max_thrust=3.0e6, reactionless=True),
            initial_position=plan_result.position, initial_velocity=plan_result.velocity,
            flight_plan=flight_plan, max_integration_dt=DEFAULT_DT_MAX)
        self.parked = False
        self.mission_active = False
        self.historical_active = True
        self.mission_target = MOON_TRIP_NAME
        self.mission_departure_time = self.sim_time_s

        self.moon_trip = True
        self.moon_state = MoonMissionState(
            return_at=self.sim_time_s + plan_result.time_of_flight,
            r1=plan_result.r1, mu_earth=plan_result.mu_earth)
        self.time_step_index = 5   # "1 hour": responsive at this scale

        self.trail = TrailPath(min_separation_km=MOON_TRAIL_KM, max_points=4000)
        self.trail.add(self.sim_ship.position)

        self.follow_target = "Earth"
        self.auto_play = False
        tof_days = plan_result.time_of_flight / 86400.0
        self.mission_label = f"{MOON_TRIP_NAME}: Hohmann to the Moon and back (~{tof_days:.1f} d each way)"
        self.last_notification = f"{MOON_TRIP_NAME} ready. Press space to fly to the Moon and back."

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_trajectory(self) -> dict[str, Any]:
        if self.sim_ship is None or len(self.sim_ship.history) < 2:
            return {"status": "empty", "message": "Nothing to export -- fly a mission first."}
        os.makedirs(EXPORT_DIR, exist_ok=True)
        basename = (self.mission_target if self.historical_active
                   else f"{self.home_body}_to_{self.mission_target or 'free'}")
        stamp = f"{self.current_date:%Y%m%dT%H%M%S}"
        filename = f"{basename}_{stamp}.csv".replace(" ", "_")
        path = os.path.join(EXPORT_DIR, filename)
        rows = export_csv(self.sim_ship, path, start_time_s=self.mission_departure_time)
        return {"status": "ok", "rows": rows, "path": path}

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def set_play(self, playing: bool) -> None:
        self.auto_play = playing

    def reverse(self) -> None:
        self.play_direction *= -1.0

    def set_time_step(self, index: int) -> None:
        self.time_step_index = max(0, min(index, len(simulation_steps) - 1))

    def set_follow(self, target: str) -> None:
        if target in self.bodies or target == "Ship":
            self.follow_target = target

    def set_home(self, body: str) -> bool:
        """Park the craft around `body`, ending any active mission (mirrors
        app.py's _set_home)."""
        if body not in self.bodies:
            return False
        self.home_body = body
        self.parked = True
        self.sim_ship = None
        self.mission_active = False
        self.historical_active = False
        self.moon_trip = False
        self.moon_state = None
        self.mission_label = ""
        self.trail = TrailPath(min_separation_km=INTERPLANETARY_TRAIL_KM, max_points=4000)
        self.follow_target = body
        return True

    def toggle_test_drive(self) -> bool:
        self.use_test_ship = not self.use_test_ship
        return self.use_test_ship
