"""
Reactive orbit-insertion tests.

These drive a real `Spaceship` (and therefore the real Verlet integrator
and sub-stepping) so they check the closed loop: the instruction reads the
live state, sizes a burn, and the physics responds — until the ship is
circularized. Earth sits at the origin and is stationary, so "relative to
the body" is just the ship's own state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from core.flight_plan import FlightPlan, OrbitInsertionInstruction
from core.physics import circular_orbit_velocity
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


def powerful_ship(position: Vec3,
                  velocity: Vec3,
                  flight_plan: FlightPlan) -> Spaceship:
    """A ship with thrust to spare, so insertion converges quickly."""
    engine = PropulsionSystem(max_thrust=5.0e6,
                              specific_impulse=450.0,
                              exhaust_velocity=4500.0,
                              fuel_mass=2.0e5)
    return Spaceship(structure_mass=2000.0,
                     payload_mass=500.0,
                     main_propulsion=engine,
                     initial_position=position,
                     initial_velocity=velocity,
                     flight_plan=flight_plan,
                     max_integration_dt=5.0)


def radial_and_tangential(ship: Spaceship, earth: StubEarth) -> tuple[float, float]:
    """Speed components (km/s) along and across the Earth-relative radius."""
    relative_position = ship.position - earth.position
    relative_velocity = ship.velocity - earth.velocity
    radial_hat = relative_position.normalized()
    radial_speed = relative_velocity.dot(radial_hat)
    tangential_speed = (relative_velocity - radial_hat * radial_speed).magnitude()
    return radial_speed, tangential_speed


class TestDormant:
    def test_coasts_and_burns_no_fuel_when_far(self) -> None:
        earth = StubEarth()
        plan = FlightPlan().add_orbit_insertion("Earth", target_altitude_km=500.0)
        # Well outside the capture radius (~6871 km), drifting slowly.
        ship = powerful_ship(position=Vec3(50000.0, 0.0, 0.0),
                             velocity=Vec3(0.0, 1.0, 0.0),
                             flight_plan=plan)
        fuel_before = ship.main_propulsion.fuel_mass
        for _ in range(20):
            ship.step_forward(dt=5.0, bodies={"Earth": earth})
        assert ship.main_propulsion.fuel_mass == fuel_before
        assert not plan.is_complete()


class TestCircularization:
    def test_overspeed_tangential_is_trimmed_to_circular(self) -> None:
        """
        Start at the target radius moving tangentially but 40% too fast.
        The (retrograde-braking) instruction must shed the excess down to
        the local circular speed and report itself complete, leaving a
        bound orbit. (It brakes rather than circularizes, so the orbit may
        be mildly eccentric; the contract is "bound near circular speed".)
        """
        earth = StubEarth()
        radius = EARTH_RADIUS + 500.0
        circular_speed = circular_orbit_velocity(EARTH_MASS, radius)
        plan = FlightPlan().add_orbit_insertion("Earth", target_altitude_km=500.0)
        ship = powerful_ship(position=Vec3(radius, 0.0, 0.0),
                             velocity=Vec3(0.0, 1.4 * circular_speed, 0.0),  # ccw, too fast
                             flight_plan=plan)

        for _ in range(400):
            ship.step_forward(dt=5.0, bodies={"Earth": earth})
            if plan.is_complete():
                break

        assert plan.is_complete()
        relative_speed = (ship.velocity - earth.velocity).magnitude()
        local_circular = circular_orbit_velocity(EARTH_MASS, ship.position.magnitude())
        escape_speed = local_circular * 2 ** 0.5
        # Speed trimmed to ~circular (so well below escape -> bound).
        assert relative_speed == pytest.approx(local_circular, rel=0.05)
        assert relative_speed < escape_speed
        # Stayed in the ecliptic plane.
        assert abs(ship.position.z) < 1.0
        assert abs(ship.velocity.z) < 1e-6

    def test_resulting_orbit_is_bound_when_coasting(self) -> None:
        """After insertion the craft stays bound (radius stays finite/contained)."""
        earth = StubEarth()
        radius = EARTH_RADIUS + 500.0
        circular_speed = circular_orbit_velocity(EARTH_MASS, radius)
        plan = FlightPlan().add_orbit_insertion("Earth", target_altitude_km=500.0)
        ship = powerful_ship(position=Vec3(radius, 0.0, 0.0),
                             velocity=Vec3(0.0, 1.25 * circular_speed, 0.0),
                             flight_plan=plan)

        for _ in range(600):
            ship.step_forward(dt=5.0, bodies={"Earth": earth})
            if plan.is_complete():
                break
        assert plan.is_complete()

        radius_after_insertion = ship.position.magnitude()
        # Plan exhausted -> coasts. Over a long coast it must stay bound:
        # braking to ~circular caps the semi-major axis, so the radius can
        # never grow past ~2x the insertion radius.
        max_radius = radius_after_insertion
        for _ in range(4000):
            ship.step_forward(dt=5.0, bodies={"Earth": earth})
            max_radius = max(max_radius, ship.position.magnitude())
        assert max_radius < 2.2 * radius_after_insertion


class TestUnitBehaviour:
    def test_reports_incomplete_until_captured(self) -> None:
        instruction = OrbitInsertionInstruction("Earth", target_altitude_km=500.0)
        assert not instruction.is_complete()

    def test_reset_clears_capture_and_insertion(self) -> None:
        earth = StubEarth()
        radius = EARTH_RADIUS + 500.0
        circular_speed = circular_orbit_velocity(EARTH_MASS, radius)
        plan = FlightPlan().add_orbit_insertion("Earth", target_altitude_km=500.0)
        ship = powerful_ship(position=Vec3(radius, 0.0, 0.0),
                             velocity=Vec3(0.0, 1.3 * circular_speed, 0.0),
                             flight_plan=plan)
        for _ in range(400):
            ship.step_forward(dt=5.0, bodies={"Earth": earth})
            if plan.is_complete():
                break
        assert plan.is_complete()

        plan.reset()
        assert not plan.is_complete()
        instruction = plan.instructions[0]
        assert isinstance(instruction, OrbitInsertionInstruction)
        assert not instruction._capturing
        assert not instruction._inserted
