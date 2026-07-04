from __future__ import annotations
import os
from math import pi, sqrt
from ursina import camera, color as ursina_color

from app_ursina.config import (EXPORT_DIR, GRID_DEPARTURE_SAMPLES,
                               GRID_FLIGHT_SAMPLES, HISTORICAL_CAMERA_Z,
                               INSERTION_ALTITUDE_KM, MAX_DEPARTURE_WINDOW_S,
                               MCC_FRACTIONS, MIN_MCC_LEAD_S,
                               MISSION_SHIP_MAX_DT, MOON_PARKING_ALTITUDE_KM,
                               MOON_TRIP_NAME, SHIP_NAME)
from app_ursina.entities import SizeMode
from app_ursina.geometry import hex_to_color, linspace
from core.export import export_csv
from core.flight_plan import FlightPlan
from core.lambert import MU_SUN, LambertNoConvergence, solve_lambert
from core.mission_planner import Objective
from core.missions import HistoricalMission
from core.physics import G, circular_orbit_velocity
from core.propagator import DEFAULT_DT_MAX
from core.spaceship import PropulsionSystem, Spaceship


class MissionMixin:
    """FLY_TO planning/launch, historical mission replay, the Earth-Moon
    trip, and mid-course corrections."""

    def _make_historical_ship(self, mission: HistoricalMission) -> Spaceship:
        """A coasting craft at a real spacecraft's recorded launch-era state."""
        return Spaceship(structure_mass=mission.structure_mass,
                         payload_mass=0.0,
                         main_propulsion=PropulsionSystem(),     # inert: it coasts
                         initial_position=mission.position,
                         initial_velocity=mission.velocity,
                         flight_plan=FlightPlan(),
                         max_integration_dt=DEFAULT_DT_MAX)

    def _load_mission(self, name: str) -> None:
        """Load a mission from the menu (a real spacecraft, or the Moon trip)."""
        if name == MOON_TRIP_NAME:
            self._load_moon_mission()
            return
        self._close_menus()
        mission = self.missions[name]
        # The craft's epoch is JD(TDB); place the clock there relative to the
        # app's ephemeris epoch so craft and planets share the same instant.
        self.sim_time_s = (mission.epoch_jd - self.ephemeris.epoch_jd) * 86400.0
        self._sync_bodies_to_time(self.sim_time_s)

        self.sim_ship = self._make_historical_ship(mission)
        self.parked = False
        self.mission_active = False
        self.historical_active = True
        self.moon_trip = False
        self.mission_target = name
        self.mission_departure_time = self.sim_time_s

        entity = self.ships[SHIP_NAME]
        entity.set_color(hex_to_color(mission.color))
        entity.trail.clear()
        entity.sync(self.sim_ship.position)

        if mission.follow in self.follow_names:
            self.follow(mission.follow)
        camera.z = HISTORICAL_CAMERA_Z
        self.camera_rig.target_z = HISTORICAL_CAMERA_Z

        self.auto_play = False
        entity.trail.path.min_separation_km = 2.0e6   # interplanetary trail spacing
        self.mission_label = f"{name}: {mission.description}"
        self._notify(f"{name} loaded at {self.current_date:%Y-%m-%d}. Press space to fly.")
        self.refresh_positions()
        self.refresh_hud()

    def _load_moon_mission(self) -> None:
        """
        A made-up Earth->Moon->Earth trip (not a real mission): one prograde burn
        from a low parking orbit raises apogee to the Moon's distance — a Hohmann
        transfer. The closed ellipse coasts out to the Moon and falls back to
        Earth on its own; departure is phased so apogee meets the Moon, giving a
        lunar flyby on the way. Flown under full N-body gravity with the
        reactionless test drive, so the burn is free.
        """
        self._close_menus()
        self.sim_time_s = 0.0                      # the app's epoch ("now")
        self._sync_bodies_to_time(self.sim_time_s)
        earth = self.bodies["Earth"]
        moon = self.bodies["Moon"]
        # G is SI (m^3/kg/s^2); positions are km, so mu must be km^3/s^2.
        mu_earth: float = G * earth.mass / 1.0e9

        r1: float = earth.radius + MOON_PARKING_ALTITUDE_KM
        # Iterate the transfer time and the Moon's arrival state together: the
        # apogee must match where the Moon will be after the transfer, and the
        # transfer time depends on that distance.
        moon_future = moon.position - earth.position
        moon_velocity = moon.velocity - earth.velocity
        for _ in range(3):
            r2: float = moon_future.magnitude()
            semi_major: float = 0.5 * (r1 + r2)
            tof: float = pi * sqrt(semi_major ** 3 / mu_earth)
            arrival_earth = self.ephemeris.state("Earth", self.sim_time_s + tof)
            arrival_moon = self.ephemeris.state("Moon", self.sim_time_s + tof)
            moon_future = arrival_moon[0] - arrival_earth[0]
            moon_velocity = arrival_moon[1] - arrival_earth[1]

        # Inject directly onto the Hohmann transfer. A 180-degree transfer puts
        # apogee opposite the perigee, so place the perigee on the far side from
        # the Moon's arrival point (in 3D, accounting for the Moon's ~5deg
        # inclination), with the perigee velocity aimed along the Moon's motion.
        # A LEO->Moon transfer is ~99% of escape speed, so apogee is
        # hypersensitive to that velocity — injecting the exact value is far
        # more reliable than delivering the kick over a finite burn.
        apogee_dir = moon_future.normalized()
        perigee_dir = apogee_dir * -1.0
        # Perigee velocity: perpendicular to the radius, along the Moon's motion.
        prograde = (moon_velocity - perigee_dir * moon_velocity.dot(perigee_dir)).normalized()
        v_transfer: float = sqrt(mu_earth * (2.0 / r1 - 1.0 / semi_major))
        position = earth.position + perigee_dir * r1
        velocity = earth.velocity + prograde * v_transfer
        plan = FlightPlan().add_coast(duration=2.2 * tof)           # out and back

        self.sim_ship = Spaceship(
            structure_mass=5000.0, payload_mass=0.0,
            main_propulsion=PropulsionSystem(max_thrust=3.0e6, reactionless=True),
            initial_position=position, initial_velocity=velocity,
            flight_plan=plan, max_integration_dt=DEFAULT_DT_MAX)
        self.parked = False
        self.mission_active = False
        self.historical_active = True              # full N-body flight (with a plan)
        self.mission_target = MOON_TRIP_NAME
        self.mission_departure_time = self.sim_time_s
        # Schedule a return burn at arrival (~apogee, near the Moon): the lunar
        # flyby would otherwise fling the craft off course, so drop it onto a
        # return ellipse back to Earth (a free burn for the reactionless drive).
        self.moon_trip = True
        self._moon_returning = True
        self._moon_descending = False
        self._moon_arrived = False
        self._moon_return_at = self.sim_time_s + tof
        self._moon_r1 = r1
        self._moon_mu = mu_earth
        self.time_step_index = 5                    # "1 hour": responsive at this scale

        entity = self.ships[SHIP_NAME]
        entity.set_color(hex_to_color("#d8d8d8"))
        entity.trail.path.min_separation_km = 5000.0   # fine trail for the Earth-Moon scale
        entity.trail.clear()
        entity.sync(self.sim_ship.position)

        self.size_mode = SizeMode.REAL             # Earth & Moon as dots at this scale
        self.follow("Earth")
        camera.z = -0.2
        self.camera_rig.target_z = -0.2

        self.auto_play = False
        self.mission_label = f"{MOON_TRIP_NAME}: Hohmann to the Moon and back (~{tof/86400.0:.1f} d each way)"
        self._notify(f"{MOON_TRIP_NAME} ready. Press space to fly to the Moon and back.")
        self.refresh_positions()
        self.refresh_hud()

    def _moon_return_burn(self) -> None:
        """At the Moon, drop the craft onto a return ellipse back to Earth."""
        earth = self.bodies["Earth"]
        relative_position = self.sim_ship.position - earth.position
        radius = relative_position.magnitude()
        radial_hat = relative_position.normalized()
        relative_velocity = self.sim_ship.velocity - earth.velocity
        tangential = relative_velocity - radial_hat * relative_velocity.dot(radial_hat)
        # Apogee speed of an ellipse with apogee = here, perigee = parking orbit.
        semi_major = 0.5 * (self._moon_r1 + radius)
        return_speed = sqrt(self._moon_mu * (2.0 / radius - 1.0 / semi_major))
        # Reactionless cheat: set the velocity directly to the return state.
        self.sim_ship._velocity = earth.velocity + tangential.normalized() * return_speed
        self._notify(f"{MOON_TRIP_NAME}: at the Moon — return burn, heading back to Earth.")

    def _moon_circularize_burn(self) -> None:
        """Back at Earth: circularize into a stable low orbit (trip complete)."""
        earth = self.bodies["Earth"]
        relative_position = self.sim_ship.position - earth.position
        radius = relative_position.magnitude()
        radial_hat = relative_position.normalized()
        relative_velocity = self.sim_ship.velocity - earth.velocity
        tangential = (relative_velocity - radial_hat * relative_velocity.dot(radial_hat)).normalized()
        v_circular = circular_orbit_velocity(earth.mass, radius)
        self.sim_ship._velocity = earth.velocity + tangential * v_circular
        self._notify(f"{MOON_TRIP_NAME}: back at Earth — circularized into low orbit. Trip complete!")

    def _notify(self, message: str) -> None:
        self.note_text.text = message

    def _export_trajectory(self) -> None:
        """Write the current craft's recorded flight to exports/<...>.csv."""
        if self.sim_ship is None or len(self.sim_ship.history) < 2:
            self._notify("Nothing to export — fly a mission first.")
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        if self.historical_active:
            basename = self.mission_target            # the mission's name
        else:
            basename = f"{self.home_body}_to_{self.mission_target or 'free'}"
        stamp = f"{self.current_date:%Y%m%dT%H%M%S}"
        filename = f"{basename}_{stamp}.csv".replace(" ", "_")
        path = os.path.join(EXPORT_DIR, filename)
        # start_time_s = mission start, so the exported time_s is absolute
        # simulation time (epoch + time_s reconstructs the calendar date).
        rows = export_csv(self.sim_ship, path, start_time_s=self.mission_departure_time)
        self._notify(f"Exported {rows} states -> exports/{filename}")

    def _transfer_grid(self, origin: str, target: str) -> tuple[list[float], list[float]]:
        """
        A porkchop search grid: departures over (up to) one synodic period
        starting now, and flight times bracketing the Hohmann time between
        the two bodies' current radii.
        """
        now: float = self.sim_time_s
        r1: float = self.ephemeris.state(origin, now)[0].magnitude()
        r2: float = self.ephemeris.state(target, now)[0].magnitude()
        semi_major: float = 0.5 * (r1 + r2)
        hohmann_tof: float = pi * sqrt(semi_major**3 / MU_SUN)
        flight_times: list[float] = linspace(0.6 * hohmann_tof, 1.6 * hohmann_tof,
                                             GRID_FLIGHT_SAMPLES)

        period_origin: float = self.bodies[origin].orbital_period * 86400.0
        period_target: float = self.bodies[target].orbital_period * 86400.0
        rate_difference: float = abs(1.0 / period_origin - 1.0 / period_target)
        synodic: float = (1.0 / rate_difference) if rate_difference > 0 else period_target
        window: float = min(synodic, MAX_DEPARTURE_WINDOW_S)
        departure_times: list[float] = linspace(now, now + window, GRID_DEPARTURE_SAMPLES)
        return departure_times, flight_times

    def _capture_radius(self, target: str) -> float:
        """
        Capture shell at a fraction of the sphere of influence: it only has
        to be wide enough to reliably latch the approach. The insertion then
        coasts down to periapsis and circularizes there, so the *resulting*
        orbit is low and well inside the SOI (stable against the Sun's
        tide), regardless of how wide this shell is.
        """
        body = self.bodies[target]
        sun = self.bodies["Sun"]
        target_radius: float = self.ephemeris.state(target, self.sim_time_s)[0].magnitude()
        sphere_of_influence: float = target_radius * (body.mass / sun.mass) ** 0.4
        return 0.5 * sphere_of_influence

    def _make_mission_ship(self, position, velocity, plan) -> Spaceship:
        """A craft with ample thrust and fuel to fly the transfer and insert."""
        if self.use_test_ship:
            # Reactionless cheat drive: unlimited delta-v, constant mass.
            engine = PropulsionSystem(max_thrust=3.0e6, reactionless=True)
        else:
            engine = PropulsionSystem(max_thrust=3.0e6,
                                      specific_impulse=450.0,
                                      exhaust_velocity=4500.0,
                                      fuel_mass=1.2e5)
        return Spaceship(structure_mass=4000.0,
                         payload_mass=1000.0,
                         main_propulsion=engine,
                         initial_position=position,
                         initial_velocity=velocity,
                         flight_plan=plan,
                         max_integration_dt=MISSION_SHIP_MAX_DT)

    def _fly_to(self, target: str) -> None:
        """Plan the cheapest transfer to `target` and launch the mission."""
        self._set_fly_menu(False)
        if target == self.home_body:
            return
        origin = self.home_body
        try:
            departures, flights = self._transfer_grid(origin, target)
            solution = self.planner.plan_transfer(
                origin=origin, target=target,
                departure_times=departures, flight_times=flights,
                objective=Objective.MIN_DELTA_V)
        except LambertNoConvergence:
            self.mission_label = f"no {origin}->{target} window found"
            self.refresh_hud()
            return

        capture_km = self._capture_radius(target)
        # Circularize well above the surface (a fraction of the SOI) rather
        # than at the centre-aimed periapsis: the transfer aims at the
        # planet centre, so the natural periapsis grazes the surface, where
        # a fast deep burn can't be integrated cleanly. Braking higher up
        # gives a high but *bound and stable* orbit (well inside the SOI).
        # A true low orbit needs B-plane targeting (future work).
        insertion_altitude = max(INSERTION_ALTITUDE_KM,
                                 0.15 * capture_km - self.bodies[target].radius)
        # Retrograde capture: budget enough to brake the arrival excess into
        # a bound orbit, with margin for the gravitational speed-up on the
        # way down to the circularization altitude.
        insertion_budget = 3.0 * solution.arrival_delta_v.magnitude() + 2.0
        plan = self.planner.to_flight_plan(
            solution, burn_duration=600.0, orbit_insertion=True,
            insertion_altitude_km=insertion_altitude,
            capture_radius_km=capture_km,
            insertion_max_delta_v_km_s=insertion_budget)
        self._launch_mission(solution, plan, capture_km, insertion_budget, insertion_altitude)

    def _launch_mission(self, solution, plan, capture_km: float,
                        insertion_budget: float, insertion_altitude: float) -> None:
        """Warp the clock to the launch window and place the craft at origin."""
        self.sim_time_s = solution.departure_time
        self._sync_bodies_to_time(self.sim_time_s)
        position, velocity = self.ephemeris.state(solution.origin, solution.departure_time)
        self.sim_ship = self._make_mission_ship(position, velocity, plan)
        self.parked = False

        entity = self.ships[SHIP_NAME]
        entity.set_color(ursina_color.azure)
        entity.trail.path.min_separation_km = 2.0e6   # interplanetary trail spacing
        entity.trail.clear()
        entity.sync(self.sim_ship.position)

        self.mission_active = True
        self.historical_active = False
        self.moon_trip = False
        self.mission_target = solution.target
        self.mission_departure_time = solution.departure_time
        self.mission_arrival_time = solution.arrival_time
        self.mission_capture_km = capture_km
        self.mission_insertion_budget = insertion_budget
        self.mission_insertion_altitude = insertion_altitude
        self.mission_gravity_bodies = {"Sun": self.bodies["Sun"],
                                       solution.target: self.bodies[solution.target]}
        self._mcc_index = 0

        self.auto_play = False
        self.mission_label = (f"{solution.origin} -> {solution.target}  "
                              f"dv {solution.total_delta_v:.2f} km/s  "
                              f"tof {solution.time_of_flight / 86400.0:.0f} d  "
                              f"(press space)")
        self.refresh_positions()
        self.refresh_hud()

    def _maybe_correct_course(self) -> None:
        """
        Re-solve Lambert from the live state and burn the correction when
        the transfer passes a scheduled mid-course-correction fraction.
        This is what keeps the craft on course to a *moving* target despite
        the coarse plan, the (smeared) finite burns and N-body drift.
        """
        if (not self.mission_active or self.sim_ship is None
                or self._mcc_index >= len(MCC_FRACTIONS)):
            return
        total: float = self.mission_arrival_time - self.mission_departure_time
        remaining: float = self.mission_arrival_time - self.sim_time_s
        if total <= 0.0:
            return
        progress: float = 1.0 - remaining / total
        if progress < MCC_FRACTIONS[self._mcc_index]:
            return
        self._mcc_index += 1

        if remaining < MIN_MCC_LEAD_S:
            return
        target_position = self.ephemeris.state(self.mission_target,
                                               self.mission_arrival_time)[0]
        # Inside the capture shell the insertion controller takes over.
        if (self.sim_ship.position - self.bodies[self.mission_target].position
                ).magnitude() < self.mission_capture_km:
            return
        try:
            lambert = solve_lambert(r1=self.sim_ship.position,
                                    r2=target_position,
                                    time_of_flight=remaining,
                                    mu=MU_SUN)
        except LambertNoConvergence:
            return
        correction = lambert.v1 - self.sim_ship.velocity
        if correction.magnitude() < 1.0e-4:   # km/s, negligible
            return
        self.sim_ship.flight_plan = (
            FlightPlan()
            .add_delta_v_vector(delta_v_vector_km_s=correction, duration=600.0)
            .add_orbit_insertion(body=self.mission_target,
                                 target_altitude_km=self.mission_insertion_altitude,
                                 capture_radius_km=self.mission_capture_km,
                                 max_delta_v_km_s=self.mission_insertion_budget))
