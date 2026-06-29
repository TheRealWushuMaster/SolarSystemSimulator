"""
Integrator tests.

The headline property is energy conservation: a symplectic integrator
(Velocity Verlet) keeps a circular orbit circular over many revolutions,
whereas first-order Euler steadily pumps energy in and the orbit drifts.
These tests pin that difference down quantitatively.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from core.integrator import AccelerationField, SemiImplicitEuler, VelocityVerlet
from core.physics import G, circular_orbit_state, circular_orbit_velocity, gravitational_acceleration
from core.vec3 import Vec3

EARTH_MASS: float = 5.97e24    # kg
EARTH_RADIUS: float = 6371.0   # km


@dataclass
class StubEarth:
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    mass: float = EARTH_MASS
    radius: float = EARTH_RADIUS


def specific_orbital_energy(position: Vec3, velocity: Vec3) -> float:
    """
    Specific mechanical energy v^2/2 - mu/r (J/kg) about Earth at origin.
    Conserved exactly for the true orbit; the integrator's drift in this
    number is the thing we are measuring. Worked in SI (m, m/s).
    """
    mu: float = G * EARTH_MASS                       # m^3/s^2
    speed_m_s: float = velocity.magnitude() * 1000.0
    radius_m: float = position.magnitude() * 1000.0
    return 0.5 * speed_m_s * speed_m_s - mu / radius_m


def earth_gravity_field() -> AccelerationField:
    earth = StubEarth()
    bodies = {"Earth": earth}
    return lambda position: gravitational_acceleration(position, bodies)


# ----------------------------------------------------------------------
# Exactness on simple fields
# ----------------------------------------------------------------------

class TestConstantField:
    def test_verlet_is_exact_for_constant_acceleration(self) -> None:
        """Under constant a, x = x0 + v0 t + 1/2 a t^2 exactly; Verlet must match."""
        integrator = VelocityVerlet()
        acceleration = Vec3(0.0, -2.0, 0.0)
        position, velocity = Vec3(0.0, 0.0, 0.0), Vec3(3.0, 0.0, 0.0)

        new_position, new_velocity, _ = integrator.step(
            position, velocity, lambda _: acceleration, dt=5.0)

        assert new_position.x == pytest.approx(15.0)             # 3 * 5
        assert new_position.y == pytest.approx(-25.0)            # 0.5 * -2 * 25
        assert new_velocity.x == pytest.approx(3.0)
        assert new_velocity.y == pytest.approx(-10.0)            # -2 * 5

    def test_zero_field_is_straight_line(self) -> None:
        for integrator in (SemiImplicitEuler(), VelocityVerlet()):
            position, velocity, _ = integrator.step(
                Vec3(1.0, 2.0, 3.0), Vec3(1.0, 0.0, -1.0), lambda _: Vec3(), dt=10.0)
            assert position == Vec3(11.0, 2.0, -7.0)
            assert velocity == Vec3(1.0, 0.0, -1.0)


# ----------------------------------------------------------------------
# Energy conservation over many orbits
# ----------------------------------------------------------------------

class TestEnergyConservation:
    @staticmethod
    def _run(integrator, dt: float, steps: int) -> float:
        """Integrate a circular LEO orbit and return |relative energy drift|."""
        field_fn = earth_gravity_field()
        position, velocity = circular_orbit_state(StubEarth(), altitude_km=418.0)
        energy_0 = specific_orbital_energy(position, velocity)

        for _ in range(steps):
            position, velocity, _ = integrator.step(position, velocity, field_fn, dt)

        energy_1 = specific_orbital_energy(position, velocity)
        return abs((energy_1 - energy_0) / energy_0)

    def test_verlet_energy_drift_is_small_over_many_orbits(self) -> None:
        # ISS-altitude period ~5560 s; at dt=60 that is ~93 steps/orbit.
        # 20 orbits is ~1850 steps.
        drift = self._run(VelocityVerlet(), dt=60.0, steps=1850)
        assert drift < 1e-3

    def test_verlet_beats_euler_decisively(self) -> None:
        steps, dt = 1850, 60.0
        verlet_drift = self._run(VelocityVerlet(), dt, steps)
        euler_drift = self._run(SemiImplicitEuler(), dt, steps)
        # Verlet should hold energy at least an order of magnitude better.
        assert verlet_drift < euler_drift / 10.0

    def test_verlet_holds_energy_at_large_steps(self) -> None:
        """
        The step size that wrecked the original sim. At dt=300 s (5 min,
        only ~18 steps/orbit) Verlet still holds the orbital *energy* — and
        hence the semi-major axis — to well under 1%. (The instantaneous
        radius does oscillate: a coarse symplectic step induces a small
        spurious eccentricity. Energy, not radius, is the invariant it
        protects, and the original Euler sim drifted that energy away.)
        """
        verlet_drift = self._run(VelocityVerlet(), dt=300.0, steps=400)   # ~22 orbits
        euler_drift = self._run(SemiImplicitEuler(), dt=300.0, steps=400)
        assert verlet_drift < 0.01
        assert verlet_drift < euler_drift / 10.0


# ----------------------------------------------------------------------
# Which point the reported acceleration is taken at
# ----------------------------------------------------------------------

class TestReportedAcceleration:
    def test_verlet_reports_acceleration_at_new_position(self) -> None:
        field_fn = earth_gravity_field()
        position, velocity = circular_orbit_state(StubEarth(), altitude_km=418.0)
        new_position, _, acceleration = VelocityVerlet().step(position, velocity, field_fn, dt=60.0)
        assert acceleration == field_fn(new_position)

    def test_euler_reports_acceleration_at_old_position(self) -> None:
        field_fn = earth_gravity_field()
        position, velocity = circular_orbit_state(StubEarth(), altitude_km=418.0)
        _, _, acceleration = SemiImplicitEuler().step(position, velocity, field_fn, dt=60.0)
        assert acceleration == field_fn(position)


def test_circular_orbit_velocity_sanity() -> None:
    """Guard: the helper the tests lean on still gives ISS-like speed."""
    speed = circular_orbit_velocity(EARTH_MASS, EARTH_RADIUS + 418.0)
    assert speed == pytest.approx(7.66, rel=0.01)
