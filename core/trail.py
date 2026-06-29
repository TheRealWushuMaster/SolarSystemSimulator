"""
Trajectory trail accumulation.

A spaceship leaves a persistent trail of every place it has been. Storing
one point per simulation step would be wasteful — a long coast is nearly
a straight line — so `TrailPath` only records a new vertex once the craft
has moved a minimum distance from the last recorded one (distance-based
decimation). An optional cap turns the trail into a ring buffer so very
long missions don't grow without bound.

This module is pure (no Ursina): the renderer reads `points` and turns
them into a line mesh. Keeping the logic here makes it unit-testable.
"""

from __future__ import annotations

from core.vec3 import Vec3


class TrailPath:
    def __init__(self,
                 min_separation_km: float,
                 max_points: int | None = None) -> None:
        if min_separation_km <= 0:
            raise ValueError("min_separation_km must be positive.")
        if max_points is not None and max_points < 2:
            raise ValueError("max_points must be at least 2 (a line needs two ends).")
        self.min_separation_km: float = min_separation_km
        self.max_points: int | None = max_points
        self.points: list[Vec3] = []

    def add(self, point: Vec3) -> bool:
        """
        Record `point` if it is the first, or far enough from the last
        recorded point. Returns True when a vertex was actually added,
        so the renderer knows whether the mesh needs regenerating.
        """
        if not self.points:
            self.points.append(point)
            return True
        if (point - self.points[-1]).magnitude() >= self.min_separation_km:
            self.points.append(point)
            if self.max_points is not None and len(self.points) > self.max_points:
                self.points.pop(0)
            return True
        return False

    def clear(self) -> None:
        self.points.clear()

    def __len__(self) -> int:
        return len(self.points)
