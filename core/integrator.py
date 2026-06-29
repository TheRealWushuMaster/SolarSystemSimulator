"""
Numerical integrators for the equations of motion.

The spaceship advances by repeatedly solving x'' = a(x): given a position,
a velocity and an acceleration field, produce the state one step later.
*How* that step is taken is the integrator's job; this module isolates it
so the choice of method is a swappable strategy and can be unit-tested on
its own (the key test being energy conservation over many orbits).

Why this matters: the original simulation used semi-implicit Euler, which
is only first-order accurate. It holds together at short steps (a few
seconds) but drifts badly at tens of minutes, which made long transfers
impractical to integrate directly. `VelocityVerlet` is second-order and
*symplectic*: its energy error stays bounded instead of growing without
limit, so a circular orbit stays circular over many revolutions at the
same per-step cost (one acceleration evaluation, reusing the previous
step's end acceleration as the next step's start).

The acceleration field is a plain `position -> acceleration` callable.
Gravity depends only on position, which is what lets Verlet stay cheap;
thrust, which also depends on mass and throttle, is folded into the field
as a term that is constant over a single (sub-)step by the caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import override

from core.vec3 import Vec3

# acceleration (km/s^2) as a function of position (km).
AccelerationField = Callable[[Vec3], Vec3]


class Integrator(ABC):
    """A single-step solver for x'' = a(x)."""

    @abstractmethod
    def step(self,
             position: Vec3,
             velocity: Vec3,
             acceleration_at: AccelerationField,
             dt: float) -> tuple[Vec3, Vec3, Vec3]:
        """
        Advance one step of `dt` seconds.

        Returns `(new_position, new_velocity, acceleration)`, where the
        acceleration is the value the caller should record for this step
        (each integrator documents which point it is evaluated at).
        """
        ...


class SemiImplicitEuler(Integrator):
    """
    First-order symplectic Euler: the method the original simulation used.

    Acceleration is evaluated once at the current position; the velocity
    is updated first and the *new* velocity advances the position. Kept
    as a baseline to integrate against (e.g. to show how much less it
    drifts than Verlet).
    """

    @override
    def step(self,
             position: Vec3,
             velocity: Vec3,
             acceleration_at: AccelerationField,
             dt: float) -> tuple[Vec3, Vec3, Vec3]:
        acceleration: Vec3 = acceleration_at(position)
        new_velocity: Vec3 = velocity + acceleration * dt
        new_position: Vec3 = position + new_velocity * dt
        return new_position, new_velocity, acceleration


class VelocityVerlet(Integrator):
    """
    Second-order symplectic Verlet — the recommended default for orbits.

    The position is advanced with a half-step of acceleration, the field
    is re-evaluated at the new position, and the velocity is advanced with
    the average of the two accelerations:

        x1 = x0 + v0*dt + 1/2 a0 dt^2
        v1 = v0 + 1/2 (a0 + a1) dt

    The acceleration returned is `a1` (at the new position), which the
    caller can reuse as the next step's `a0` to keep this to one field
    evaluation per step when the field is position-only.
    """

    @override
    def step(self,
             position: Vec3,
             velocity: Vec3,
             acceleration_at: AccelerationField,
             dt: float) -> tuple[Vec3, Vec3, Vec3]:
        acceleration_start: Vec3 = acceleration_at(position)
        new_position: Vec3 = position + velocity * dt + acceleration_start * (0.5 * dt * dt)
        acceleration_end: Vec3 = acceleration_at(new_position)
        new_velocity: Vec3 = velocity + (acceleration_start + acceleration_end) * (0.5 * dt)
        return new_position, new_velocity, acceleration_end
