"""
Mission planner: turns "fly to Mars" into a concrete flight plan.

The approach is the classic porkchop search used in real mission design:

  1. Lay out a grid of candidate (departure time, time of flight) pairs.
  2. For each pair, ask the ephemeris where the origin body is at
     departure and where the target body will be at arrival, then solve
     Lambert's problem between those two points.
  3. The difference between the Lambert departure velocity and the
     origin body's own velocity is the delta-v you must burn to leave;
     the difference at arrival is the delta-v to match the target.
  4. Score every grid point by the chosen objective and keep the best.

The planner never talks to the GUI or to jplephem directly: it sees the
solar system only through the `Ephemeris` protocol, so tests can drive
it with analytic circular orbits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import pi, sqrt
from typing import Protocol, override

from core.flight_plan import FlightPlan
from core.lambert import MU_SUN, LambertNoConvergence, solve_lambert
from core.vec3 import Vec3

# Porkchop grid defaults, matching the desktop app's GRID_*/MAX_DEPARTURE_WINDOW_S.
DEFAULT_GRID_DEPARTURE_SAMPLES: int = 24
DEFAULT_GRID_FLIGHT_SAMPLES: int = 12
DEFAULT_MAX_DEPARTURE_WINDOW_S: float = 3.0 * 365.25 * 86400.0


def linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step: float = (stop - start) / (count - 1)
    return [start + step * i for i in range(count)]


class OrbitingBody(Protocol):
    """The minimal view of a body needed for the porkchop grid / capture radius."""

    @property
    def mass(self) -> float: ...

    @property
    def orbital_period(self) -> float: ...


class Ephemeris(Protocol):
    """Source of body states. Time is seconds from an arbitrary epoch."""

    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]:
        """Return (position km, velocity km/s) of `body` at `time_s`."""
        ...


class Objective(Enum):
    MIN_DELTA_V = auto()   # least total fuel
    MIN_TIME = auto()      # fastest arrival within the delta-v budget


@dataclass(frozen=True)
class TransferSolution:
    """One feasible transfer found by the planner."""
    origin: str
    target: str
    departure_time: float        # s from epoch
    time_of_flight: float        # s
    departure_delta_v: Vec3      # km/s, relative to the origin body
    arrival_delta_v: Vec3        # km/s, relative to the target body

    @property
    def arrival_time(self) -> float:
        return self.departure_time + self.time_of_flight

    @property
    def total_delta_v(self) -> float:
        """Total delta-v cost (km/s): departure burn + arrival matching burn."""
        return self.departure_delta_v.magnitude() + self.arrival_delta_v.magnitude()

    @override
    def __repr__(self) -> str:
        days: float = self.time_of_flight / 86400.0
        return (f"TransferSolution({self.origin} -> {self.target}, "
                f"depart t={self.departure_time:.6g} s, "
                f"tof={days:.1f} d, dv={self.total_delta_v:.3f} km/s)")


@dataclass(frozen=True)
class PorkchopPoint:
    """One grid cell of the porkchop search (for plotting later)."""
    departure_time: float
    time_of_flight: float
    total_delta_v: float | None   # None where Lambert has no solution


class MissionPlanner:
    """
    Searches transfer windows between two bodies orbiting the same
    central mass and converts the best solution to a FlightPlan.
    """

    def __init__(self, ephemeris: Ephemeris, mu: float = MU_SUN) -> None:
        self.ephemeris: Ephemeris = ephemeris
        self.mu: float = mu

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def evaluate_transfer(self,
                          origin: str,
                          target: str,
                          departure_time: float,
                          time_of_flight: float) -> TransferSolution | None:
        """
        Solve one grid point: Lambert from origin's position at
        departure to target's position at arrival. Returns None where
        no single-revolution transfer exists.
        """
        r1, v_origin = self.ephemeris.state(origin, departure_time)
        r2, v_target = self.ephemeris.state(target, departure_time + time_of_flight)
        try:
            lambert = solve_lambert(r1=r1, r2=r2,
                                    time_of_flight=time_of_flight,
                                    mu=self.mu)
        except LambertNoConvergence:
            return None
        return TransferSolution(origin=origin,
                                target=target,
                                departure_time=departure_time,
                                time_of_flight=time_of_flight,
                                departure_delta_v=lambert.v1 - v_origin,
                                arrival_delta_v=v_target - lambert.v2)

    def porkchop(self,
                 origin: str,
                 target: str,
                 departure_times: list[float],
                 flight_times: list[float]) -> list[PorkchopPoint]:
        """
        Evaluate the whole (departure x flight time) grid. The result
        is the raw material both for plotting and for `plan_transfer`.
        """
        grid: list[PorkchopPoint] = []
        for departure_time in departure_times:
            for time_of_flight in flight_times:
                solution = self.evaluate_transfer(origin=origin,
                                                  target=target,
                                                  departure_time=departure_time,
                                                  time_of_flight=time_of_flight)
                grid.append(PorkchopPoint(
                    departure_time=departure_time,
                    time_of_flight=time_of_flight,
                    total_delta_v=solution.total_delta_v if solution is not None else None,
                ))
        return grid

    def plan_transfer(self,
                      origin: str,
                      target: str,
                      departure_times: list[float],
                      flight_times: list[float],
                      objective: Objective = Objective.MIN_DELTA_V,
                      delta_v_budget_km_s: float | None = None) -> TransferSolution:
        """
        Search the grid and return the best transfer per the objective.

          * MIN_DELTA_V: cheapest total delta-v.
          * MIN_TIME: earliest arrival among transfers whose total
            delta-v fits within `delta_v_budget_km_s`.
        """
        if objective is Objective.MIN_TIME and delta_v_budget_km_s is None:
            raise ValueError("MIN_TIME requires a delta_v_budget_km_s.")

        best: TransferSolution | None = None
        for departure_time in departure_times:
            for time_of_flight in flight_times:
                solution = self.evaluate_transfer(origin=origin,
                                                  target=target,
                                                  departure_time=departure_time,
                                                  time_of_flight=time_of_flight)
                if solution is None:
                    continue
                if objective is Objective.MIN_DELTA_V:
                    if best is None or solution.total_delta_v < best.total_delta_v:
                        best = solution
                else:  # MIN_TIME
                    assert delta_v_budget_km_s is not None
                    if solution.total_delta_v > delta_v_budget_km_s:
                        continue
                    if best is None or solution.arrival_time < best.arrival_time:
                        best = solution
        if best is None:
            raise LambertNoConvergence(
                f"No feasible {origin} -> {target} transfer found in the "
                f"searched window."
            )
        return best

    def transfer_grid(self,
                      origin: str,
                      target: str,
                      now: float,
                      bodies: dict[str, OrbitingBody],
                      grid_departure_samples: int = DEFAULT_GRID_DEPARTURE_SAMPLES,
                      grid_flight_samples: int = DEFAULT_GRID_FLIGHT_SAMPLES,
                      max_departure_window_s: float = DEFAULT_MAX_DEPARTURE_WINDOW_S,
                      ) -> tuple[list[float], list[float]]:
        """
        A porkchop search grid: departures over (up to) one synodic period
        starting now, and flight times bracketing the Hohmann time between
        the two bodies' current radii.
        """
        r1: float = self.ephemeris.state(origin, now)[0].magnitude()
        r2: float = self.ephemeris.state(target, now)[0].magnitude()
        semi_major: float = 0.5 * (r1 + r2)
        hohmann_tof: float = pi * sqrt(semi_major**3 / self.mu)
        flight_times: list[float] = linspace(0.6 * hohmann_tof, 1.6 * hohmann_tof,
                                             grid_flight_samples)

        period_origin: float = bodies[origin].orbital_period * 86400.0
        period_target: float = bodies[target].orbital_period * 86400.0
        rate_difference: float = abs(1.0 / period_origin - 1.0 / period_target)
        synodic: float = (1.0 / rate_difference) if rate_difference > 0 else period_target
        window: float = min(synodic, max_departure_window_s)
        departure_times: list[float] = linspace(now, now + window, grid_departure_samples)
        return departure_times, flight_times

    def capture_radius(self, target: str, sim_time_s: float,
                       bodies: dict[str, OrbitingBody]) -> float:
        """
        Capture shell at a fraction of the sphere of influence: it only has
        to be wide enough to reliably latch the approach. The insertion then
        coasts down to periapsis and circularizes there, so the *resulting*
        orbit is low and well inside the SOI (stable against the Sun's
        tide), regardless of how wide this shell is.
        """
        body = bodies[target]
        sun = bodies["Sun"]
        target_radius: float = self.ephemeris.state(target, sim_time_s)[0].magnitude()
        sphere_of_influence: float = target_radius * (body.mass / sun.mass) ** 0.4
        return 0.5 * sphere_of_influence

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    def to_flight_plan(self,
                       solution: TransferSolution,
                       burn_duration: float = 600.0,
                       orbit_insertion: bool = False,
                       insertion_altitude_km: float = 500.0,
                       capture_radius_km: float | None = None,
                       insertion_max_delta_v_km_s: float = 6.0) -> FlightPlan:
        """
        Convert a transfer solution to executable instructions:

          1. A vector delta-v burn to inject onto the transfer (the
             Lambert departure delta-v, `v1 - v_origin`, which generally
             does not point along the origin's velocity — so it must be a
             vector burn, not a prograde change of speed).
          2. Coast for (most of) the transfer duration.
          3. Arrival, in one of two styles:
             * default (`orbit_insertion=False`): a vector delta-v burn to
               match the target's velocity, parking the craft alongside it.
             * `orbit_insertion=True`: a reactive `OrbitInsertionInstruction`
               that waits until the craft is captured and circularizes
               into orbit. This subsumes the arrival burn (it kills the
               arrival excess velocity itself), so no matching burn is
               added.

        This is the patched-conic idealization: each burn is treated as
        impulsive at the level of the plan, and the simulation's real
        physics then shows how close the idealization gets.
        """
        if orbit_insertion:
            # End the timed coast a little before nominal arrival so the
            # (reactive, dormant-until-captured) insertion is already the
            # active instruction as the craft closes in.
            coast_duration: float = (solution.time_of_flight - burn_duration) * 0.9
            if coast_duration <= 0:
                raise ValueError("Burn duration too long for this transfer's "
                                 "time of flight.")
            return (FlightPlan()
                    .add_delta_v_vector(delta_v_vector_km_s=solution.departure_delta_v,
                                        duration=burn_duration)
                    .add_coast(duration=coast_duration)
                    .add_orbit_insertion(body=solution.target,
                                         target_altitude_km=insertion_altitude_km,
                                         capture_radius_km=capture_radius_km,
                                         max_delta_v_km_s=insertion_max_delta_v_km_s))

        coast_duration = solution.time_of_flight - 2.0 * burn_duration
        if coast_duration <= 0:
            raise ValueError("Burn duration too long for this transfer's "
                             "time of flight.")
        return (FlightPlan()
                .add_delta_v_vector(delta_v_vector_km_s=solution.departure_delta_v,
                                    duration=burn_duration)
                .add_coast(duration=coast_duration)
                .add_delta_v_vector(delta_v_vector_km_s=solution.arrival_delta_v,
                                    duration=burn_duration))
