"""
Adaptive N-body propagation for a coasting craft.

A real interplanetary craft (e.g. a historical mission replay) coasts under
the gravity of the whole system. Far from any planet a long step is fine;
during a flyby the step must shrink or the slingshot integrates inaccurately.

`advance_coasting` walks the craft forward with a step sized from its distance
to the nearest planet, re-syncing the bodies to the ephemeris at every
sub-step so a fast encounter sees the planet where it really is (the same
fix the GUI uses for its missions, generalised to all bodies). It validated
against JPL HORIZONS for Voyager 1's Jupiter flyby — closest approach within
~3% on the correct date.

Pure (no GUI): it reads/writes the bodies' state through their `position` /
`velocity` and steps the ship.
"""

from __future__ import annotations

from typing import Protocol

from core.physics import GravitatingBody
from core.spaceship import Spaceship
from core.vec3 import Vec3

DEFAULT_STEP_FRACTION: float = 0.005   # move at most this fraction of the
DEFAULT_DT_MIN: float = 2.0            # nearest-planet distance per step,
DEFAULT_DT_MAX: float = 43200.0        # clamped to [2 s, 12 h]


class Ephemeris(Protocol):
    """Source of body states (matches core.ephemeris.JplEphemeris)."""

    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]: ...


def adaptive_dt(ship: Spaceship,
                bodies: dict[str, GravitatingBody],
                step_fraction: float = DEFAULT_STEP_FRACTION,
                dt_min: float = DEFAULT_DT_MIN,
                dt_max: float = DEFAULT_DT_MAX) -> float:
    """
    A sub-step that moves the craft at most `step_fraction` of its distance to
    the nearest planet (the Sun is excluded — the craft never leaves its broad
    well), clamped to [dt_min, dt_max]. Tiny through a flyby, large in cruise.
    """
    nearest_distance: float = float("inf")
    nearest: GravitatingBody | None = None
    for name, body in bodies.items():
        if name == "Sun":
            continue
        distance: float = (ship.position - body.position).magnitude()
        if distance < nearest_distance:
            nearest_distance, nearest = distance, body
    if nearest is None:
        return dt_max
    relative_speed: float = (ship.velocity - nearest.velocity).magnitude()
    dt: float = step_fraction * nearest_distance / max(relative_speed, 1.0)
    return max(dt_min, min(dt_max, dt))


def advance_coasting(ship: Spaceship,
                     ephemeris: Ephemeris,
                     bodies: dict[str, GravitatingBody],
                     time_s: float,
                     dt_s: float,
                     step_fraction: float = DEFAULT_STEP_FRACTION,
                     dt_min: float = DEFAULT_DT_MIN,
                     dt_max: float = DEFAULT_DT_MAX) -> None:
    """
    Advance `ship` from absolute `time_s` by `dt_s` under full N-body gravity,
    re-syncing every body from `ephemeris` at each adaptive sub-step. The ship
    must have `max_integration_dt >= dt_max` so each `step_forward` is a single
    Verlet sub-step of the size chosen here.
    """
    target: float = time_s + dt_s
    current: float = time_s
    while current < target - 1e-6:
        for name, body in bodies.items():
            position, velocity = ephemeris.state(name, current)
            body.position = position
            body.velocity = velocity
        sub_dt: float = min(adaptive_dt(ship, bodies, step_fraction, dt_min, dt_max),
                            target - current)
        ship.step_forward(sub_dt, bodies)
        current += sub_dt
