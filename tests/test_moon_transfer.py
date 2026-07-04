from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, pi, sin, sqrt

import pytest

from core.moon_transfer import MoonMissionPhase, MoonMissionState, plan_moon_transfer
from core.physics import G, circular_orbit_velocity
from core.vec3 import Vec3

EARTH_MASS: float = 5.97e24
EARTH_RADIUS: float = 6371.0
MOON_DISTANCE: float = 384400.0
MU_EARTH: float = G * EARTH_MASS / 1.0e9


@dataclass(frozen=True)
class StubBody:
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    mass: float = EARTH_MASS
    radius: float = EARTH_RADIUS


class CircularMoonEphemeris:
    """Earth fixed at the origin; the Moon on a circular orbit around it."""

    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]:
        if body == "Earth":
            return Vec3(), Vec3()
        angular_rate = sqrt(MU_EARTH / MOON_DISTANCE**3)
        angle = angular_rate * time_s
        speed = sqrt(MU_EARTH / MOON_DISTANCE)
        position = Vec3(MOON_DISTANCE * cos(angle), MOON_DISTANCE * sin(angle), 0.0)
        velocity = Vec3(-speed * sin(angle), speed * cos(angle), 0.0)
        return position, velocity


@dataclass
class StubShip:
    position: Vec3
    velocity: Vec3
    _velocity: Vec3 = field(init=False)

    def __post_init__(self) -> None:
        self._velocity = self.velocity


class TestPlanMoonTransfer:
    def test_injection_reaches_parking_radius(self) -> None:
        earth = StubBody()
        ephemeris = CircularMoonEphemeris()
        moon_position, moon_velocity = ephemeris.state("Moon", 0.0)
        moon = StubBody(position=moon_position, velocity=moon_velocity)
        plan = plan_moon_transfer(earth, moon, ephemeris, sim_time_s=0.0,
                                  parking_altitude_km=500.0)
        assert plan.position.magnitude() == pytest.approx(EARTH_RADIUS + 500.0)
        assert plan.time_of_flight > 0.0

    def test_transfer_is_faster_than_lunar_orbit(self) -> None:
        """A one-way Hohmann transfer to the Moon should take roughly
        4-6 days -- much less than the Moon's own ~27.3 day orbit."""
        earth = StubBody()
        ephemeris = CircularMoonEphemeris()
        moon_position, moon_velocity = ephemeris.state("Moon", 0.0)
        moon = StubBody(position=moon_position, velocity=moon_velocity)
        plan = plan_moon_transfer(earth, moon, ephemeris, sim_time_s=0.0)
        days = plan.time_of_flight / 86400.0
        assert 3.0 < days < 7.0


class TestMoonMissionState:
    def test_outbound_until_return_time(self) -> None:
        earth = StubBody()
        state = MoonMissionState(return_at=1000.0, r1=EARTH_RADIUS + 500.0, mu_earth=MU_EARTH)
        # Ship far from Earth, moving away -- still outbound before return_at.
        ship = StubShip(position=Vec3(300000.0, 0.0, 0.0), velocity=Vec3(0.0, 0.5, 0.0))
        assert state.step(ship, earth, sim_time_s=500.0) == MoonMissionPhase.OUTBOUND

    def test_return_burn_fires_at_scheduled_time(self) -> None:
        earth = StubBody()
        state = MoonMissionState(return_at=1000.0, r1=EARTH_RADIUS + 500.0, mu_earth=MU_EARTH)
        ship = StubShip(position=Vec3(300000.0, 0.0, 0.0), velocity=Vec3(0.0, 0.5, 0.0))
        phase = state.step(ship, earth, sim_time_s=1000.0)
        assert phase == MoonMissionPhase.RETURN_COAST
        # The return burn re-aims the ship onto a (slower) descending ellipse:
        # speed drops and the radial component point back toward Earth.
        assert ship._velocity.magnitude() < 0.5

    def test_circularizes_at_first_perigee_after_return(self) -> None:
        earth = StubBody()
        state = MoonMissionState(return_at=0.0, r1=EARTH_RADIUS + 500.0, mu_earth=MU_EARTH)
        state._returning = False   # simulate having already fired the return burn
        # Descending (negative range rate)...
        descending_ship = StubShip(position=Vec3(300000.0, 0.0, 0.0),
                                   velocity=Vec3(-1.0, 0.0, 0.0))
        phase = state.step(descending_ship, earth, sim_time_s=1.0)
        assert phase == MoonMissionPhase.RETURN_COAST
        assert state._descending

        # ...then the range rate flips positive (perigee passed): circularize.
        radius = EARTH_RADIUS + 500.0
        rising_ship = StubShip(position=Vec3(radius, 0.0, 0.0), velocity=Vec3(1.0, 5.0, 0.0))
        phase = state.step(rising_ship, earth, sim_time_s=2.0)
        assert phase == MoonMissionPhase.CIRCULARIZED
        expected_speed = circular_orbit_velocity(EARTH_MASS, radius)
        assert rising_ship._velocity.magnitude() == pytest.approx(expected_speed)
