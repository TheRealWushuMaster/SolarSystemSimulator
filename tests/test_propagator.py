"""Adaptive N-body propagator tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from core.flight_plan import FlightPlan
from core.physics import circular_orbit_velocity
from core.propagator import DEFAULT_DT_MAX, adaptive_dt, advance_coasting
from core.spaceship import PropulsionSystem, Spaceship
from core.vec3 import Vec3

SUN_MASS: float = 1.9885e30
SUN_RADIUS: float = 695700.0
AU: float = 1.495978707e8


@dataclass
class Stub:
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    mass: float = SUN_MASS
    radius: float = SUN_RADIUS


class SunOnlyEphemeris:
    """A single stationary Sun at the origin."""
    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]:
        return Vec3(), Vec3()


class TestAdaptiveDt:
    def test_far_from_planets_uses_max(self) -> None:
        ship = Stub(position=Vec3(AU, 0.0, 0.0), velocity=Vec3(0.0, 30.0, 0.0))
        bodies = {"Sun": Stub(), "Mars": Stub(position=Vec3(-2 * AU, 0.0, 0.0))}
        assert adaptive_dt(ship, bodies, dt_max=43200.0) == 43200.0

    def test_close_to_planet_shrinks(self) -> None:
        ship = Stub(position=Vec3(AU + 50000.0, 0.0, 0.0), velocity=Vec3(0.0, 30.0, 0.0))
        jupiter = Stub(position=Vec3(AU, 0.0, 0.0), velocity=Vec3(0.0, 13.0, 0.0))
        bodies = {"Sun": Stub(), "Jupiter": jupiter}
        dt = adaptive_dt(ship, bodies, step_fraction=0.005, dt_min=30.0, dt_max=43200.0)
        assert dt < 43200.0
        assert dt >= 30.0

    def test_sun_is_ignored(self) -> None:
        # Only the Sun present -> no planet -> falls back to dt_max.
        ship = Stub(position=Vec3(AU, 0.0, 0.0), velocity=Vec3(0.0, 30.0, 0.0))
        assert adaptive_dt(ship, {"Sun": Stub()}, dt_max=999.0) == 999.0


class TestAdvanceCoasting:
    def test_circular_orbit_radius_holds(self) -> None:
        """A craft coasting around the (stationary) Sun keeps its radius."""
        radius = 1.2 * AU
        speed = circular_orbit_velocity(SUN_MASS, radius)
        ship = Spaceship(structure_mass=1000.0, payload_mass=0.0,
                         main_propulsion=PropulsionSystem(),
                         initial_position=Vec3(radius, 0.0, 0.0),
                         initial_velocity=Vec3(0.0, speed, 0.0),
                         flight_plan=FlightPlan(),
                         max_integration_dt=DEFAULT_DT_MAX)
        bodies = {"Sun": Stub()}
        ephemeris = SunOnlyEphemeris()

        # ~30 days, capped to a fine fixed step (no planets -> adaptive=dt_max,
        # so force a small dt_max for accuracy here).
        advance_coasting(ship, ephemeris, bodies, time_s=0.0,
                         dt_s=30.0 * 86400.0, dt_max=600.0)

        assert ship.position.magnitude() == pytest.approx(radius, rel=0.01)
        assert len(ship.history) > 1            # it actually integrated steps

    def test_advances_full_interval(self) -> None:
        radius = 1.0 * AU
        speed = circular_orbit_velocity(SUN_MASS, radius)
        ship = Spaceship(structure_mass=1000.0, payload_mass=0.0,
                         main_propulsion=PropulsionSystem(),
                         initial_position=Vec3(radius, 0.0, 0.0),
                         initial_velocity=Vec3(0.0, speed, 0.0),
                         flight_plan=FlightPlan(),
                         max_integration_dt=DEFAULT_DT_MAX)
        # Sum of the recorded sub-step dt's should equal the requested span.
        advance_coasting(ship, SunOnlyEphemeris(), {"Sun": Stub()},
                         time_s=0.0, dt_s=5.0 * 86400.0, dt_max=3600.0)
        total = sum(snap.time_step for snap in ship.history)
        assert total == pytest.approx(5.0 * 86400.0)
