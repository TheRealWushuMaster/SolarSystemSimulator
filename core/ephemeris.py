"""
Adapter between JPL ephemeris kernels and the planner's `Ephemeris`
protocol.

The mission planner asks one question: "where is body X at time t?"
(`state(body, time_s) -> (position, velocity)`). A JPL SPK kernel
answers a slightly different one: it stores Chebyshev polynomials for
*segments* — body relative to its parent barycenter, e.g. Earth
relative to the Earth-Moon barycenter relative to the Solar System
barycenter. This module walks those segment chains and converts units:

  * jplephem returns positions in km and velocities in km/day;
    the simulation works in km and km/s.
  * the planner uses seconds from an arbitrary epoch; the kernel is
    indexed by Julian date. The adapter anchors the epoch at
    construction time.

By default states are returned heliocentric (relative to the Sun),
which is the frame the Lambert solver works in. Pass `center=None`
for raw Solar-System-barycenter states.
"""

from __future__ import annotations

from typing import Protocol

from core.vec3 import Vec3

SECONDS_PER_DAY: float = 86400.0


class SpkSegment(Protocol):
    """One segment of an SPK kernel (jplephem's segment interface)."""

    def compute_and_differentiate(self, tdb: float) -> tuple:
        """Return (position km, velocity km/day) as array-likes."""
        ...


class SpkKernel(Protocol):
    """The subset of `jplephem.spk.SPK` the adapter needs."""

    def __getitem__(self, key: tuple[int, int]) -> SpkSegment: ...


class JplEphemeris:
    """
    Implements the planner's `Ephemeris` protocol on top of an SPK
    kernel.

    `location_paths` maps body names to their SPICE target chains as
    already stored in data/bodies.json — e.g. Earth is [0, 3, 399]:
    Solar System barycenter -> Earth-Moon barycenter -> Earth.
    """

    def __init__(self,
                 kernel: SpkKernel,
                 location_paths: dict[str, list[int]],
                 epoch_jd: float,
                 center: str | None = "Sun") -> None:
        for name, path in location_paths.items():
            if len(path) < 2:
                raise ValueError(f"Location path of '{name}' needs at "
                                 f"least two SPICE ids, got {path}.")
        if center is not None and center not in location_paths:
            raise ValueError(f"Center body '{center}' has no location path.")
        self.kernel: SpkKernel = kernel
        self.location_paths: dict[str, list[int]] = location_paths
        self.epoch_jd: float = epoch_jd
        self.center: str | None = center

    @classmethod
    def from_bodies(cls,
                    kernel: SpkKernel,
                    bodies: dict,
                    epoch_jd: float,
                    center: str | None = "Sun") -> JplEphemeris:
        """Build from a dict of core `CelestialBody` objects."""
        location_paths: dict[str, list[int]] = {
            name: body.location_path for name, body in bodies.items()
        }
        return cls(kernel=kernel,
                   location_paths=location_paths,
                   epoch_jd=epoch_jd,
                   center=center)

    # ------------------------------------------------------------------
    # Ephemeris protocol
    # ------------------------------------------------------------------

    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]:
        """
        Position (km) and velocity (km/s) of `body` at `time_s` seconds
        after the adapter's epoch, relative to `center`.
        """
        jd: float = self.epoch_jd + time_s / SECONDS_PER_DAY
        position, velocity = self._barycentric_state(body, jd)
        if self.center is not None and body != self.center:
            center_position, center_velocity = self._barycentric_state(self.center, jd)
            position = position - center_position
            velocity = velocity - center_velocity
        elif self.center is not None:
            # The center relative to itself is at rest at the origin.
            return Vec3(), Vec3()
        return position, velocity

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _barycentric_state(self, body: str, jd: float) -> tuple[Vec3, Vec3]:
        """Sum the segment chain to get the SSB-relative state."""
        if body not in self.location_paths:
            raise KeyError(f"Body '{body}' has no location path.")
        path: list[int] = self.location_paths[body]
        position: Vec3 = Vec3()
        velocity: Vec3 = Vec3()
        for origin, target in zip(path[:-1], path[1:]):
            segment: SpkSegment = self.kernel[origin, target]
            segment_position, segment_velocity = segment.compute_and_differentiate(jd)
            position = position + Vec3(float(segment_position[0]),
                                       float(segment_position[1]),
                                       float(segment_position[2]))
            velocity = velocity + Vec3(float(segment_velocity[0]) / SECONDS_PER_DAY,
                                       float(segment_velocity[1]) / SECONDS_PER_DAY,
                                       float(segment_velocity[2]) / SECONDS_PER_DAY)
        return position, velocity
