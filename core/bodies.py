from __future__ import annotations
import json
from math import pi
from pathlib import Path
from typing import Any, override
from core.vec3 import Vec3

_BODIES_JSON: Path = Path(__file__).parent.parent / "data" / "bodies.json"


def _color_index_to_rgb(color_index: float) -> str:
    """Convert B-V color index to an approximate hex RGB color."""
    color_temp: float = 4600 * (
        1 / (0.92 * color_index + 1.7) + 1 / (0.92 * color_index + 0.62)
    )
    if color_temp <= 6600:
        r: int = 255
        g: int = max(0, min(255, int((color_temp - 2000) / 25)))
        b: int = 0
    else:
        r = max(0, min(255, int((color_temp - 6000) / 25)))
        g = max(0, min(255, int((color_temp - 4000) / 15)))
        b = max(0, min(255, int((color_temp - 2000) / 6)))
    return f"#{r:02x}{g:02x}{b:02x}".upper()


class CelestialBody:
    """
    Base class for all gravitational bodies.

    Position and velocity are stored as plain floats (x, y, z) so that
    ephemeris code can update them directly, but the `position` and
    `velocity` properties expose them as Vec3 for physics calculations.
    `circumference` and `rotation_period` are derived automatically and
    do not need to be stored or passed in.
    """

    def __init__(self,
                 name: str,
                 radius: float,
                 mass: float,
                 temperature: float,
                 rotation_velocity: float,
                 parent_body: str | None,
                 location_path: list[int],
                 average_orbital_speed: float,
                 orbital_period: float,
                 texture: str | None = None,
                 rings: int = 0,
                 axial_tilt_deg: float = 0.0) -> None:
        self.name: str = name
        self.radius: float = radius
        self.mass: float = mass
        self.temperature: float = temperature
        self.rotation_velocity: float = rotation_velocity
        self.parent_body: str | None = parent_body
        self.location_path: list[int] = location_path
        self.average_orbital_speed: float = average_orbital_speed
        self.orbital_period: float = orbital_period
        self.texture: str | None = texture
        self.rings: int = rings
        self.axial_tilt_deg: float = axial_tilt_deg

        # Set by ephemeris at runtime; start at origin.
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.velocity_x: float = 0.0
        self.velocity_y: float = 0.0
        self.velocity_z: float = 0.0

        # Render cache for orbital path; populated by graphics layer.
        self.orbit_points: list = []

        # Subclasses must set self.color.
        self.color: str = "#ffffff"

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def circumference(self) -> float:
        return 2 * pi * self.radius

    @property
    def rotation_period(self) -> float:
        if self.rotation_velocity == 0:
            return 0.0
        return self.circumference / self.rotation_velocity

    @property
    def position(self) -> Vec3:
        return Vec3(self.x, self.y, self.z)

    @position.setter
    def position(self, v: Vec3) -> None:
        self.x, self.y, self.z = v.x, v.y, v.z

    @property
    def velocity(self) -> Vec3:
        return Vec3(self.velocity_x, self.velocity_y, self.velocity_z)

    @velocity.setter
    def velocity(self, v: Vec3) -> None:
        self.velocity_x, self.velocity_y, self.velocity_z = v.x, v.y, v.z

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def return_position_vector(self,
                               normalized: bool = True,
                               coefficient: float = 1.0) -> Vec3:
        v: Vec3 = Vec3(self.x, self.y, self.z)
        if normalized:
            v: Vec3 = v.normalized()
        return v * coefficient

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, position={self.position})"


class Star(CelestialBody):
    """A stellar body. Color is derived automatically from color_index."""

    def __init__(self,
                 name: str,
                 star_type: str,
                 luminosity: float,
                 color_index: float,
                 **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.star_type: str = star_type
        self.luminosity: float = luminosity
        self.color_index: float = color_index
        self.color: str = _color_index_to_rgb(color_index)


class Planet(CelestialBody):
    """A planetary body or moon."""

    def __init__(self,
                 name: str,
                 planet_type: str,
                 color: str,
                 atmosphere: int = 0,
                 surface: int = 0,
                 **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.planet_type: str = planet_type
        self.color: str = color
        self.atmosphere: int = atmosphere
        self.surface: int = surface


def load_bodies_from_json(path: Path = _BODIES_JSON) -> dict[str, CelestialBody]:
    """Load celestial bodies from data/bodies.json."""
    with open(path) as f:
        data: dict[str, Any] = json.load(f)
    bodies: dict[str, CelestialBody] = {}
    for name, props in data.get("stars", {}).items():
        bodies[name] = Star(name=name, **props)
    for name, props in data.get("planets", {}).items():
        bodies[name] = Planet(name=name, **props)
    for name, props in data.get("moons", {}).items():
        bodies[name] = Planet(name=name, **props)
    return bodies
