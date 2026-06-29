"""
Core physics helpers, free of GUI and settings imports.

Unit conventions (matching the rest of the simulation):
  * distances and positions: km
  * velocities: km/s
  * accelerations: km/s^2
  * masses: kg
  * forces: N
"""

from __future__ import annotations

from math import cos, radians, sin, sqrt
from typing import Protocol

from core.vec3 import Vec3

G: float = 6.674e-11  # m^3 kg^-1 s^-2


class GravitatingBody(Protocol):
    """The minimal view of a celestial body needed for gravity."""

    @property
    def position(self) -> Vec3: ...

    @property
    def velocity(self) -> Vec3: ...

    @property
    def mass(self) -> float: ...

    @property
    def radius(self) -> float: ...


def gravitational_acceleration(position: Vec3,
                               bodies: dict[str, GravitatingBody]) -> Vec3:
    """
    Total gravitational acceleration (km/s^2) at `position` (km) from
    all `bodies`. Contributions from inside a body's radius are ignored
    (matches the original behaviour, and avoids the singularity).
    """
    total: Vec3 = Vec3()
    for body in bodies.values():
        offset_m: Vec3 = (body.position - position) * 1000.0
        distance_m: float = offset_m.magnitude()
        if distance_m < body.radius * 1000.0:
            continue
        # G*M/d^2 gives m/s^2; divide by 1000 for km/s^2.
        acceleration_module: float = G * body.mass / distance_m**2 / 1000.0
        total = total + offset_m.normalized() * acceleration_module
    return total


def circular_orbit_velocity(body_mass: float, orbit_radius_km: float) -> float:
    """Speed (km/s) of a circular orbit of `orbit_radius_km` around `body_mass`."""
    return sqrt(G * body_mass / (orbit_radius_km * 1000.0)) / 1000.0


def circular_orbit_state(body: GravitatingBody,
                         altitude_km: float,
                         angle_deg: float = 0.0,
                         direction: str = "cw") -> tuple[Vec3, Vec3]:
    """
    Position and velocity (km, km/s) for a circular orbit around `body`
    at `altitude_km` above its surface, in the body's z-plane.

    `angle_deg` places the ship along the orbit; `direction` is "cw" or
    "ccw" as seen from +z.
    """
    orbit_radius: float = body.radius + altitude_km
    angle: float = radians(angle_deg)
    radial: Vec3 = Vec3(sin(angle), -cos(angle), 0.0)
    if direction == "cw":
        tangential: Vec3 = Vec3(-radial.y, radial.x, 0.0)
    elif direction == "ccw":
        tangential = Vec3(radial.y, -radial.x, 0.0)
    else:
        raise ValueError(f"Direction '{direction}' not recognized. Use 'cw' or 'ccw'.")
    position: Vec3 = body.position + radial * orbit_radius
    velocity: Vec3 = body.velocity + tangential * circular_orbit_velocity(body.mass, orbit_radius)
    return position, velocity
