"""
Lambert's problem solver (universal variables formulation).

Lambert's problem is the boundary-value problem of orbital mechanics:

    Given a departure position r1, an arrival position r2, and a time
    of flight, find the orbit that connects them — in particular the
    departure velocity v1 and arrival velocity v2.

Everything a mission planner does reduces to this. If you know where
the ship is, where Mars will be in 200 days, and you can solve Lambert,
you know exactly what velocity (and therefore what burn) you need today.

The implementation follows the universal-variables method as presented
in Curtis, "Orbital Mechanics for Engineering Students" (Algorithm 5.2):
the whole problem collapses to finding the root of a single scalar
function F(z), where the sign of z says whether the connecting orbit is
an ellipse (z > 0), a parabola (z = 0) or a hyperbola (z < 0). The root
is bracketed and then found by bisection, which is slower than Newton
but cannot diverge.

Units: positions in km, time in s, mu in km^3/s^2, velocities in km/s.
"""

from __future__ import annotations
from dataclasses import dataclass
from math import cos, cosh, pi, sin, sinh, sqrt
from core.vec3 import Vec3

# Gravitational parameter (mu = G*M) of the Sun, in km^3/s^2.
MU_SUN: float = 1.32712440018e11


class LambertNoConvergence(Exception):
    """Raised when no orbit can connect r1 to r2 in the given time."""


@dataclass(frozen=True)
class LambertSolution:
    v1: Vec3                # departure velocity, km/s
    v2: Vec3                # arrival velocity, km/s
    time_of_flight: float   # s (echo of the input)


def _stumpff_c(z: float) -> float:
    """Stumpff function C(z): handles ellipse/parabola/hyperbola in one expression."""
    if z > 1e-8:
        return (1.0 - cos(sqrt(z))) / z
    if z < -1e-8:
        return (cosh(sqrt(-z)) - 1.0) / (-z)
    return 0.5  # series limit at z = 0

def _stumpff_s(z: float) -> float:
    """Stumpff function S(z)."""
    sz: float
    if z > 1e-8:
        sz = sqrt(z)
        return (sz - sin(sz)) / sz**3
    if z < -1e-8:
        sz = sqrt(-z)
        return (sinh(sz) - sz) / sz**3
    return 1.0 / 6.0  # series limit at z = 0

def solve_lambert(r1: Vec3,
                  r2: Vec3,
                  time_of_flight: float,
                  mu: float = MU_SUN,
                  prograde: bool = True,
                  max_iterations: int = 200,
                  tolerance: float = 1e-8) -> LambertSolution:
    """
    Solve Lambert's problem for the single-revolution transfer from
    `r1` to `r2` in `time_of_flight` seconds around a central body of
    gravitational parameter `mu`.

    `prograde` selects the direction of travel around the central body
    (counterclockwise as seen from +z, which is how the planets orbit).
    """
    if time_of_flight <= 0:
        raise ValueError("Time of flight must be positive.")
    r1_mag: float = r1.magnitude()
    r2_mag: float = r2.magnitude()
    if r1_mag == 0.0 or r2_mag == 0.0:
        raise ValueError("Position vectors must be non-zero.")
    # Transfer angle. The cross product's z-component tells us whether
    # the short way from r1 to r2 is prograde or retrograde.
    cross: Vec3 = r1.cross(r2)
    cos_dtheta: float = r1.dot(r2) / (r1_mag * r2_mag)
    cos_dtheta = min(1.0, max(-1.0, cos_dtheta))
    from math import acos
    dtheta: float = acos(cos_dtheta)
    if prograde:
        if cross.z < 0.0:
            dtheta = 2.0 * pi - dtheta
    else:
        if cross.z >= 0.0:
            dtheta = 2.0 * pi - dtheta
    # The constant A captures the geometry of the transfer.
    sin_dtheta: float = sin(dtheta)
    A: float = sin_dtheta * sqrt(r1_mag * r2_mag / (1.0 - cos_dtheta))
    if abs(A) < 1e-12:
        raise LambertNoConvergence(
            "Transfer angle of 0 or 180 degrees: the transfer plane is " +
            "undefined (any plane through both positions works). Offset " +
            "the departure time slightly to break the degeneracy.")
    def y(z: float) -> float:
        return r1_mag + r2_mag + A * (z * _stumpff_s(z) - 1.0) / sqrt(_stumpff_c(z))
    def time_for_z(z: float) -> float:
        """Time of flight produced by a given z (the function we invert)."""
        yz: float = y(z)
        if yz < 0.0:
            return float("-inf")  # unphysical region
        return ((yz / _stumpff_c(z)) ** 1.5 * _stumpff_s(z) # pyright: ignore[reportAny]
                + A * sqrt(yz)) / sqrt(mu)
    # Bracket the root. z is bounded above by (2*pi)^2 — the limit of a
    # full-revolution ellipse, where C(z) hits zero and the time of
    # flight diverges — so stay strictly below it. The lower bound
    # (hyperbolic transfers) expands downward until the target time is
    # bracketed.
    # The margin below the singularity must be wide enough that
    # 1 - cos(sqrt(z_high)) does not round to zero in double precision;
    # 1e-4 keeps C(z_high) ~ 5e-9 while the corresponding time of
    # flight is astronomically large, so no practical solution is lost.
    z_low: float = -4.0 * pi * pi
    z_high: float = 4.0 * pi * pi * (1.0 - 1e-4)
    while time_for_z(z_low) > time_of_flight:
        z_low *= 2.0
        if z_low < -1e6:
            raise LambertNoConvergence(
                f"No hyperbolic transfer reaches the target in " +
                f"{time_of_flight:.6g} s — time of flight too short.")
    # Shrink z_high into the physical region (y >= 0, finite time).
    while time_for_z(z_high) < time_of_flight:
        z_high = z_low + (z_high - z_low) * 0.99
        if z_high - z_low < tolerance:
            raise LambertNoConvergence(
                f"No single-revolution transfer takes as long as " +
                f"{time_of_flight:.6g} s — time of flight too long.")
    # Bisection: monotonic, always converges inside the bracket.
    z: float = 0.0
    for _ in range(max_iterations):
        z = 0.5 * (z_low + z_high)
        t: float = time_for_z(z)
        if abs(t - time_of_flight) < tolerance:
            break
        if t < time_of_flight:
            z_low = z
        else:
            z_high = z
    else:
        raise LambertNoConvergence(
            f"Bisection did not converge after {max_iterations} iterations.")
    # Lagrange coefficients give the velocities from the converged z.
    yz: float = y(z)
    f: float = 1.0 - yz / r1_mag
    g: float = A * sqrt(yz / mu)
    g_dot: float = 1.0 - yz / r2_mag
    v1: Vec3 = (r2 - r1 * f) / g
    v2: Vec3 = (r2 * g_dot - r1) / g
    return LambertSolution(v1=v1,
                           v2=v2,
                           time_of_flight=time_of_flight)
