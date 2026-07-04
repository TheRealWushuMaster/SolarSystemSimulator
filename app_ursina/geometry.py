from __future__ import annotations
from math import cos, log10, pi, sin
from ursina import Mesh, Vec3 as UrsinaVec3, color as ursina_color

from app_ursina.config import POSITION_SCALE, RING_SEGMENTS
from core.vec3 import Vec3


def linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step: float = (stop - start) / (count - 1)
    return [start + step * i for i in range(count)]


def hex_to_color(hex_color: str):
    """'#RRGGBB' -> ursina color."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return ursina_color.rgba(r, g, b, 1.0)


def ecliptic_to_scene(x_km: float, y_km: float, z_km: float) -> UrsinaVec3:
    """Heliocentric ecliptic km -> ursina scene units (y-up)."""
    return UrsinaVec3(x_km * POSITION_SCALE,
                      z_km * POSITION_SCALE,
                      y_km * POSITION_SCALE)


def vec3_to_scene(v: Vec3) -> UrsinaVec3:
    return ecliptic_to_scene(v.x, v.y, v.z)


def log_diameter(radius_km: float) -> float:
    """
    Logarithmic size (scene units) so everything is visible at once:
    Moon ~0.66, Earth ~0.92, Jupiter ~1.9, Sun ~2.8 diameter.
    """
    return max(0.15, 0.2 * log10(radius_km / 10.0)) * 2.0


def real_diameter(radius_km: float) -> float:
    """True diameter in scene units (often sub-pixel)."""
    return 2.0 * radius_km * POSITION_SCALE


def make_ring_mesh(inner: float, outer: float, segments: int = RING_SEGMENTS) -> Mesh:
    """
    A flat annulus in the local xz-plane (radii in local units), with UVs
    mapping the radial direction across u (0 at the inner edge, 1 at the
    outer) so a ring texture's radial bands land in the right place.
    """
    vertices: list[UrsinaVec3] = []
    uvs: list[tuple[float, float]] = []
    triangles: list[int] = []
    for i in range(segments + 1):
        angle = 2.0 * pi * i / segments
        c, s = cos(angle), sin(angle)
        vertices.append(UrsinaVec3(inner * c, 0.0, inner * s))
        vertices.append(UrsinaVec3(outer * c, 0.0, outer * s))
        uvs.append((0.0, 0.5))
        uvs.append((1.0, 0.5))
    for i in range(segments):
        b = 2 * i
        triangles += [b, b + 1, b + 3, b, b + 3, b + 2]
    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, mode="triangle")
