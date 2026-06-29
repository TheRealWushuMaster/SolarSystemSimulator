"""Reactionless ("test") drive: thrust without losing mass."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from core.flight_plan import FlightPlan, delta_v_for_throttle, throttle_for_delta_v
from core.physics import circular_orbit_state
from core.spaceship import PropulsionSystem, Spaceship
from core.vec3 import Vec3

EARTH_MASS: float = 5.97e24
EARTH_RADIUS: float = 6371.0


@dataclass
class StubEarth:
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    mass: float = EARTH_MASS
    radius: float = EARTH_RADIUS


def make_ship(engine: PropulsionSystem, plan: FlightPlan | None = None,
              earth: StubEarth | None = None) -> Spaceship:
    earth = earth or StubEarth()
    position, velocity = circular_orbit_state(earth, altitude_km=400.0)
    return Spaceship(structure_mass=2000.0, payload_mass=500.0,
                     main_propulsion=engine,
                     initial_position=position, initial_velocity=velocity,
                     flight_plan=plan)


def test_reactionless_engine_never_runs_dry() -> None:
    engine = PropulsionSystem(max_thrust=1.0e5, reactionless=True, fuel_mass=0.0)
    assert engine.has_fuel
    assert engine.fuel_needed(1.0e5, 100.0) == 0.0


def test_mass_constant_while_thrusting() -> None:
    earth = StubEarth()
    engine = PropulsionSystem(max_thrust=1.0e6, reactionless=True, fuel_mass=0.0)
    plan = FlightPlan().add_speed_up(throttle=1.0, duration=100.0)
    ship = make_ship(engine, plan, earth)
    mass_before = ship.total_mass
    speed_before = ship.velocity.magnitude()
    for _ in range(10):
        ship.step_forward(dt=10.0, bodies={"Earth": earth})
    assert ship.total_mass == mass_before              # no propellant spent
    assert ship.velocity.magnitude() > speed_before    # but it accelerated


def test_thrusts_with_zero_fuel_unlike_real_engine() -> None:
    earth = StubEarth()
    plan = FlightPlan().add_speed_up(throttle=1.0, duration=50.0)
    # Real engine, empty tank -> no thrust.
    real = make_ship(PropulsionSystem(max_thrust=1.0e6, exhaust_velocity=4500.0,
                                      fuel_mass=0.0), plan, earth)
    v0 = real.velocity.magnitude()
    real.step_forward(dt=10.0, bodies={"Earth": earth})
    assert real.velocity.magnitude() == pytest.approx(v0, rel=1e-4)

    # Reactionless engine, empty tank -> still thrusts.
    plan2 = FlightPlan().add_speed_up(throttle=1.0, duration=50.0)
    test = make_ship(PropulsionSystem(max_thrust=1.0e6, reactionless=True,
                                      fuel_mass=0.0), plan2, earth)
    v1 = test.velocity.magnitude()
    test.step_forward(dt=10.0, bodies={"Earth": earth})
    assert test.velocity.magnitude() > v1


def test_delta_v_helpers_use_constant_mass() -> None:
    engine = PropulsionSystem(max_thrust=1.0e6, reactionless=True, fuel_mass=0.0)
    ship = make_ship(engine)
    # dv = F * throttle * dt / m  (no rocket equation).
    expected = 1.0e6 * 0.5 * 10.0 / ship.total_mass
    assert delta_v_for_throttle(ship, 0.5, 10.0) == pytest.approx(expected)
    # Inverse round-trips.
    assert throttle_for_delta_v(ship, expected, 10.0) == pytest.approx(0.5)


def test_delivers_large_delta_v_without_running_out() -> None:
    """A 5 km/s burn that a small real tank could never afford."""
    earth = StubEarth()
    engine = PropulsionSystem(max_thrust=2.0e6, reactionless=True, fuel_mass=0.0)
    plan = FlightPlan().add_delta_v(delta_v_km_s=5.0, duration=200.0,
                                    reference_body="Earth")
    ship = make_ship(engine, plan, earth)
    speed_before = ship.velocity.magnitude()
    for _ in range(40):
        ship.step_forward(dt=5.0, bodies={"Earth": earth})
        if plan.is_complete():
            break
    assert plan.is_complete()
    gained = (ship.velocity.magnitude() - speed_before) * 1000.0
    assert gained == pytest.approx(5000.0, rel=0.02)
