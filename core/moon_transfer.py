"""
The custom Earth-Moon-Earth round trip (not a real mission): a Hohmann
transfer out from a low parking orbit, a free (reactionless) return burn at
the Moon, and an event-based circularization back at Earth.

Pure (no GUI, no Ursina): the injection math and the return/circularize
state machine only touch Vec3s, an Ephemeris-like protocol, and a
Spaceship's `_velocity` field.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import pi, sqrt
from typing import Protocol

from core.physics import G, circular_orbit_velocity
from core.vec3 import Vec3


class Ephemeris(Protocol):
    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]: ...


class MoonBody(Protocol):
    @property
    def position(self) -> Vec3: ...
    @property
    def velocity(self) -> Vec3: ...
    @property
    def mass(self) -> float: ...
    @property
    def radius(self) -> float: ...


class ShipState(Protocol):
    @property
    def position(self) -> Vec3: ...
    @property
    def velocity(self) -> Vec3: ...
    _velocity: Vec3


@dataclass(frozen=True)
class MoonTransferPlan:
    """The injection state for the outbound Hohmann leg, plus what the
    return/circularize burns need later (r1, mu_earth)."""
    position: Vec3          # injection (departure) position, km
    velocity: Vec3          # injection (departure) velocity, km/s
    time_of_flight: float   # one-way Hohmann time, s
    r1: float               # parking-orbit radius, km
    mu_earth: float         # km^3/s^2


def plan_moon_transfer(earth: MoonBody, moon: MoonBody,
                       ephemeris: Ephemeris, sim_time_s: float,
                       parking_altitude_km: float = 500.0,
                       iterations: int = 3) -> MoonTransferPlan:
    """
    One prograde injection raises apogee to meet the Moon's future
    position -- a Hohmann transfer. Iterates the transfer time and the
    Moon's arrival state together: the apogee must match where the Moon
    will be after the transfer, and the transfer time depends on that
    distance.
    """
    mu_earth: float = G * earth.mass / 1.0e9   # G is SI; positions are km.
    r1: float = earth.radius + parking_altitude_km

    moon_future: Vec3 = moon.position - earth.position
    moon_velocity: Vec3 = moon.velocity - earth.velocity
    semi_major: float = 0.0
    tof: float = 0.0
    for _ in range(iterations):
        r2: float = moon_future.magnitude()
        semi_major = 0.5 * (r1 + r2)
        tof = pi * sqrt(semi_major**3 / mu_earth)
        arrival_earth = ephemeris.state("Earth", sim_time_s + tof)
        arrival_moon = ephemeris.state("Moon", sim_time_s + tof)
        moon_future = arrival_moon[0] - arrival_earth[0]
        moon_velocity = arrival_moon[1] - arrival_earth[1]

    # A 180-degree transfer puts apogee opposite the perigee, so place the
    # perigee on the far side from the Moon's arrival point (accounting for
    # its ~5deg inclination in 3D), with the perigee velocity aimed along
    # the Moon's motion. A LEO->Moon transfer is ~99% of escape speed, so
    # apogee is hypersensitive to that velocity -- injecting the exact
    # value directly is far more reliable than a finite burn.
    apogee_dir = moon_future.normalized()
    perigee_dir = apogee_dir * -1.0
    prograde = (moon_velocity - perigee_dir * moon_velocity.dot(perigee_dir)).normalized()
    v_transfer: float = sqrt(mu_earth * (2.0 / r1 - 1.0 / semi_major))
    position = earth.position + perigee_dir * r1
    velocity = earth.velocity + prograde * v_transfer
    return MoonTransferPlan(position=position, velocity=velocity,
                            time_of_flight=tof, r1=r1, mu_earth=mu_earth)


class MoonMissionPhase(Enum):
    OUTBOUND = auto()       # coasting out to the Moon, return burn not yet fired
    RETURN_COAST = auto()   # past the return burn, descending toward Earth
    CIRCULARIZED = auto()   # trip complete


class MoonMissionState:
    """
    Event-based state machine for the return leg: the return burn fires on
    a schedule (arrival at the Moon), but circularization fires on the
    first perigee *after* that burn -- detected via the sign change of the
    Earth-relative range rate -- which is robust to however large the
    (slingshot-perturbed) return ellipse turns out to be.
    """

    def __init__(self, return_at: float, r1: float, mu_earth: float) -> None:
        self.return_at: float = return_at
        self.r1: float = r1
        self.mu_earth: float = mu_earth
        self._returning: bool = True     # hasn't fired the return burn yet
        self._descending: bool = False
        self._arrived: bool = False

    @property
    def phase(self) -> MoonMissionPhase:
        if self._arrived:
            return MoonMissionPhase.CIRCULARIZED
        if not self._returning:
            return MoonMissionPhase.RETURN_COAST
        return MoonMissionPhase.OUTBOUND

    def step(self, ship: ShipState, earth: MoonBody, sim_time_s: float) -> MoonMissionPhase:
        """Advance the state machine by one tick; fires the return/circularize
        burns in place on `ship` when their trigger condition is met."""
        if self._returning and sim_time_s >= self.return_at:
            self.return_burn(ship, earth)
            self._returning = False
        elif not self._returning and not self._arrived:
            relative_position = ship.position - earth.position
            relative_velocity = ship.velocity - earth.velocity
            range_rate = relative_position.dot(relative_velocity)
            if range_rate < 0.0:
                self._descending = True
            elif self._descending:
                self.circularize_burn(ship, earth)
                self._arrived = True
        return self.phase

    def return_burn(self, ship: ShipState, earth: MoonBody) -> None:
        """At the Moon, drop the craft onto a return ellipse back to Earth."""
        relative_position = ship.position - earth.position
        radius = relative_position.magnitude()
        radial_hat = relative_position.normalized()
        relative_velocity = ship.velocity - earth.velocity
        tangential = relative_velocity - radial_hat * relative_velocity.dot(radial_hat)
        # Apogee speed of an ellipse with apogee = here, perigee = parking orbit.
        semi_major = 0.5 * (self.r1 + radius)
        return_speed = sqrt(self.mu_earth * (2.0 / radius - 1.0 / semi_major))
        ship._velocity = earth.velocity + tangential.normalized() * return_speed

    def circularize_burn(self, ship: ShipState, earth: MoonBody) -> None:
        """Back at Earth: circularize into a stable low orbit (trip complete)."""
        relative_position = ship.position - earth.position
        radius = relative_position.magnitude()
        radial_hat = relative_position.normalized()
        relative_velocity = ship.velocity - earth.velocity
        tangential = (relative_velocity - radial_hat * relative_velocity.dot(radial_hat)).normalized()
        v_circular = circular_orbit_velocity(earth.mass, radius)
        ship._velocity = earth.velocity + tangential * v_circular
