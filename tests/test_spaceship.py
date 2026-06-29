from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from core.flight_plan import FlightPlan
from core.physics import circular_orbit_state, circular_orbit_velocity, gravitational_acceleration
from core.spaceship import PropulsionSystem, Spaceship
from core.vec3 import Vec3

EARTH_MASS: float = 5.97e24    # kg
EARTH_RADIUS: float = 6371.0   # km


@dataclass
class StubEarth:
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    mass: float = EARTH_MASS
    radius: float = EARTH_RADIUS


def make_ship(flight_plan: FlightPlan | None = None,
              fuel_mass: float = 4000.0,
              takeoff: PropulsionSystem | None = None,
              altitude_km: float = 418.0,
              earth: StubEarth | None = None) -> Spaceship:
    earth = earth if earth is not None else StubEarth()
    position, velocity = circular_orbit_state(earth, altitude_km=altitude_km)
    main = PropulsionSystem(max_thrust=100000.0,
                            specific_impulse=300.0,
                            exhaust_velocity=4500.0,
                            fuel_mass=fuel_mass)
    return Spaceship(structure_mass=2000.0,
                     payload_mass=500.0,
                     main_propulsion=main,
                     initial_position=position,
                     initial_velocity=velocity,
                     takeoff_propulsion=takeoff,
                     flight_plan=flight_plan)


# ----------------------------------------------------------------------
# Physics helpers
# ----------------------------------------------------------------------

class TestPhysics:
    def test_gravity_points_at_body(self) -> None:
        earth = StubEarth()
        acceleration = gravitational_acceleration(Vec3(7000.0, 0.0, 0.0), {"Earth": earth})
        assert acceleration.x < 0
        assert acceleration.y == pytest.approx(0.0)
        assert acceleration.z == pytest.approx(0.0)

    def test_surface_gravity_magnitude(self) -> None:
        """g at Earth's surface should be ~9.81 m/s^2 (9.81e-3 km/s^2)."""
        earth = StubEarth()
        acceleration = gravitational_acceleration(Vec3(EARTH_RADIUS, 0.0, 0.0), {"Earth": earth})
        assert acceleration.magnitude() == pytest.approx(9.81e-3, rel=0.01)

    def test_no_gravity_inside_body(self) -> None:
        earth = StubEarth()
        acceleration = gravitational_acceleration(Vec3(100.0, 0.0, 0.0), {"Earth": earth})
        assert acceleration == Vec3()

    def test_iss_orbital_velocity(self) -> None:
        """ISS orbital speed is ~7.66 km/s at 418 km altitude."""
        speed = circular_orbit_velocity(EARTH_MASS, EARTH_RADIUS + 418.0)
        assert speed == pytest.approx(7.66, rel=0.01)

    def test_orbit_state_velocity_is_tangential(self) -> None:
        earth = StubEarth()
        position, velocity = circular_orbit_state(earth, altitude_km=418.0, angle_deg=30.0)
        radial = position - earth.position
        assert radial.dot(velocity) == pytest.approx(0.0, abs=1e-9)

    def test_orbit_state_invalid_direction(self) -> None:
        with pytest.raises(ValueError):
            circular_orbit_state(StubEarth(), altitude_km=418.0, direction="up")


# ----------------------------------------------------------------------
# Orbital coasting: the integration sanity check
# ----------------------------------------------------------------------

class TestOrbitalCoast:
    def test_circular_orbit_radius_is_stable(self) -> None:
        """
        A ship placed in a circular orbit and left to coast must stay at
        (approximately) the same orbital radius. One full ISS orbit is
        ~5560 s; simulate it at 10 s steps and check the radius drift.
        """
        earth = StubEarth()
        bodies = {"Earth": earth}
        ship = make_ship(earth=earth)
        initial_radius = (ship.position - earth.position).magnitude()

        for _ in range(556):
            ship.step_forward(dt=10.0, bodies=bodies)

        final_radius = (ship.position - earth.position).magnitude()
        # Semi-implicit Euler at dt=10 drifts slightly; 1% is fine here.
        assert final_radius == pytest.approx(initial_radius, rel=0.01)

    def test_coasting_consumes_no_fuel(self) -> None:
        earth = StubEarth()
        ship = make_ship(earth=earth)
        fuel_before = ship.main_propulsion.fuel_mass
        for _ in range(10):
            ship.step_forward(dt=10.0, bodies={"Earth": earth})
        assert ship.main_propulsion.fuel_mass == fuel_before


# ----------------------------------------------------------------------
# Thrust, fuel and staging
# ----------------------------------------------------------------------

class TestThrustAndFuel:
    def test_fuel_consumption_matches_thrust(self) -> None:
        """fuel = F * dt / v_e for a full-throttle burn."""
        earth = StubEarth()
        plan = FlightPlan().add_speed_up(throttle=1.0, duration=10.0)
        ship = make_ship(flight_plan=plan, earth=earth)
        fuel_before = ship.main_propulsion.fuel_mass
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        expected = 100000.0 * 10.0 / 4500.0
        assert fuel_before - ship.main_propulsion.fuel_mass == pytest.approx(expected)

    def test_no_thrust_without_fuel(self) -> None:
        earth = StubEarth()
        plan = FlightPlan().add_speed_up(throttle=1.0, duration=10.0)
        ship = make_ship(flight_plan=plan, fuel_mass=0.0, earth=earth)
        speed_before = ship.velocity.magnitude()
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        # Gravity is perpendicular to the velocity here, so any speed
        # gain from thrust would show up clearly; there must be none.
        assert ship.velocity.magnitude() == pytest.approx(speed_before, rel=1e-4)

    def test_takeoff_stage_jettisons_when_dry(self) -> None:
        earth = StubEarth()
        takeoff = PropulsionSystem(max_thrust=200000.0,
                                   specific_impulse=250.0,
                                   exhaust_velocity=2500.0,
                                   structure_mass=1500.0,
                                   fuel_mass=100.0)
        plan = FlightPlan().add_speed_up(throttle=1.0, duration=100.0)
        ship = make_ship(flight_plan=plan, takeoff=takeoff, earth=earth)
        assert not ship.takeoff_jettisoned
        mass_with_stage = ship.total_mass

        # 100 kg of fuel at 200 kN / 2500 m/s lasts 1.25 s; one 10 s
        # step must drain and drop the stage.
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        assert ship.takeoff_jettisoned
        # Stage structure (1500) and its remaining fuel (0) are gone,
        # main fuel is untouched.
        assert ship.total_mass == pytest.approx(mass_with_stage - 1500.0 - 100.0)
        assert ship.main_propulsion.fuel_mass == 4000.0

    def test_takeoff_stage_mass_counts_before_jettison(self) -> None:
        takeoff = PropulsionSystem(structure_mass=1500.0, fuel_mass=100.0)
        ship = make_ship(takeoff=takeoff)
        assert ship.total_mass == 2000.0 + 500.0 + 4000.0 + 1500.0 + 100.0

    def test_delta_v_burn_changes_speed_by_target(self) -> None:
        """
        A 0.05 km/s prograde delta-v should raise the ship's speed by
        ~50 m/s (gravity stays perpendicular, so the comparison holds).
        """
        earth = StubEarth()
        plan = FlightPlan().add_delta_v(delta_v_km_s=0.05, duration=10.0,
                                        reference_body="Earth")
        ship = make_ship(flight_plan=plan, earth=earth)
        speed_before = ship.velocity.magnitude()
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        gained_m_s = (ship.velocity.magnitude() - speed_before) * 1000.0
        assert gained_m_s == pytest.approx(50.0, rel=0.01)


# ----------------------------------------------------------------------
# History replay
# ----------------------------------------------------------------------

class TestHistory:
    def test_step_back_restores_state(self) -> None:
        earth = StubEarth()
        plan = FlightPlan().add_speed_up(throttle=1.0, duration=30.0)
        ship = make_ship(flight_plan=plan, earth=earth)
        position_0 = ship.position
        fuel_0 = ship.main_propulsion.fuel_mass

        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        ship.step_backwards()
        ship.step_backwards()

        assert ship.position == position_0
        assert ship.main_propulsion.fuel_mass == fuel_0

    def test_step_back_at_start_is_noop(self) -> None:
        ship = make_ship()
        position_0 = ship.position
        ship.step_backwards()
        assert ship.position == position_0
        assert ship.index == 0

    def test_forward_replay_matches_original(self) -> None:
        """Stepping back then forward must replay, not re-simulate."""
        earth = StubEarth()
        plan = FlightPlan().add_speed_up(throttle=1.0, duration=20.0)
        ship = make_ship(flight_plan=plan, earth=earth)

        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
        position_2 = ship.position
        velocity_2 = ship.velocity
        fuel_2 = ship.main_propulsion.fuel_mass

        ship.step_backwards()
        ship.step_forward(dt=10.0, bodies={"Earth": earth})

        assert ship.position == position_2
        assert ship.velocity == velocity_2
        assert ship.main_propulsion.fuel_mass == fuel_2
        assert len(ship.history) == 3  # no extra snapshots from the replay

    def test_trajectory_collects_positions(self) -> None:
        earth = StubEarth()
        ship = make_ship(earth=earth)
        for _ in range(5):
            ship.step_forward(dt=10.0, bodies={"Earth": earth})
        assert len(ship.trajectory) == 6  # initial + 5 steps
