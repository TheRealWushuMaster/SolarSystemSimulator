from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import override


@dataclass(frozen=True)
class Vec3:
    """Immutable 3D vector. All operations return new instances."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float) -> Vec3:
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    @override
    def __repr__(self) -> str:
        return f"Vec3({self.x:.6g}, {self.y:.6g}, {self.z:.6g})"

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(x=self.y * other.z - self.z * other.y,
                    y=self.z * other.x - self.x * other.z,
                    z=self.x * other.y - self.y * other.x)

    def magnitude(self) -> float:
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> Vec3:
        m: float = self.magnitude()
        if m == 0.0:
            raise ValueError("Cannot normalize a zero vector.")
        return Vec3(x=self.x / m,
                    y=self.y / m,
                    z=self.z / m)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)
