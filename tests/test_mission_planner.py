from __future__ import annotations

from math import cos, pi, sin, sqrt

import pytest

from core.flight_plan import (
    CoastInstruction,
    OrbitInsertionInstruction,
    VectorBurnInstruction,
)
from core.lambert import MU_SUN, LambertNoConvergence
from core.mission_planner import MissionPlanner, Objective, TransferSolution
from core.vec3 import Vec3

AU: float = 1.495978707e8  # km
DAY: float = 86400.0  # s

EARTH_ORBIT_RADIUS: float = 1.0 * AU
MARS_ORBIT_RADIUS: float = 1.524 * AU


class CircularEphemeris:
    """
    Analytic ephemeris: bodies on circular, coplanar orbits around the
    Sun. Exact two-body motion, so the planner's results can be checked
    against the closed-form Hohmann transfer.
    """

    def __init__(self, orbits: dict[str, tuple[float, float]]) -> None:
        """`orbits` maps body name to (orbit radius km, initial angle rad)."""
        self.orbits: dict[str, tuple[float, float]] = orbits

    def state(self, body: str, time_s: float) -> tuple[Vec3, Vec3]:
        radius, initial_angle = self.orbits[body]
        angular_rate: float = sqrt(MU_SUN / radius**3)
        angle: float = initial_angle + angular_rate * time_s
        speed: float = sqrt(MU_SUN / radius)
        position = Vec3(radius * cos(angle), radius * sin(angle), 0.0)
        velocity = Vec3(-speed * sin(angle), speed * cos(angle), 0.0)
        return position, velocity


def hohmann_expectations() -> tuple[float, float]:
    """Closed-form Earth->Mars Hohmann: (total delta-v km/s, tof s)."""
    r1, r2 = EARTH_ORBIT_RADIUS, MARS_ORBIT_RADIUS
    a_transfer: float = (r1 + r2) / 2.0
    v_earth: float = sqrt(MU_SUN / r1)
    v_mars: float = sqrt(MU_SUN / r2)
    v_depart: float = sqrt(MU_SUN * (2.0 / r1 - 1.0 / a_transfer))
    v_arrive: float = sqrt(MU_SUN * (2.0 / r2 - 1.0 / a_transfer))
    total_dv: float = (v_depart - v_earth) + (v_mars - v_arrive)
    tof: float = pi * sqrt(a_transfer**3 / MU_SUN)
    return total_dv, tof


@pytest.fixture
def planner() -> MissionPlanner:
    ephemeris = CircularEphemeris(orbits={
        "Earth": (EARTH_ORBIT_RADIUS, 0.0),
        "Mars": (MARS_ORBIT_RADIUS, pi / 4.0),
    })
    return MissionPlanner(ephemeris=ephemeris)


class TestEvaluateTransfer:
    def test_returns_solution_for_feasible_transfer(self, planner: MissionPlanner) -> None:
        solution = planner.evaluate_transfer(origin="Earth", target="Mars",
                                             departure_time=0.0,
                                             time_of_flight=250.0 * DAY)
        assert solution is not None
        assert solution.total_delta_v > 0.0

    def test_returns_none_for_impossible_transfer(self, planner: MissionPlanner) -> None:
        solution = planner.evaluate_transfer(origin="Earth", target="Mars",
                                             departure_time=0.0,
                                             time_of_flight=60.0)  # one minute
        assert solution is None


class TestPlannerFindsHohmann:
    def test_min_delta_v_search_approaches_hohmann(self, planner: MissionPlanner) -> None:
        """
        The whole point of the planner: searching the porkchop grid for
        minimum delta-v between two circular orbits must rediscover the
        Hohmann transfer (the provable optimum), both in cost and in
        flight time. The grid is coarse, so tolerances are loose.
        """
        expected_dv, expected_tof = hohmann_expectations()

        # Departures across ~one synodic period, 10-day steps;
        # flight times bracketing the Hohmann time, 10-day steps.
        departures: list[float] = [i * 10.0 * DAY for i in range(80)]
        flight_times: list[float] = [(150.0 + i * 10.0) * DAY for i in range(21)]

        best: TransferSolution = planner.plan_transfer(
            origin="Earth", target="Mars",
            departure_times=departures,
            flight_times=flight_times,
            objective=Objective.MIN_DELTA_V,
        )
        assert best.total_delta_v == pytest.approx(expected_dv, rel=0.05)
        assert best.time_of_flight == pytest.approx(expected_tof, rel=0.10)

    def test_min_time_respects_budget(self, planner: MissionPlanner) -> None:
        expected_dv, _ = hohmann_expectations()
        departures: list[float] = [i * 10.0 * DAY for i in range(80)]
        flight_times: list[float] = [(150.0 + i * 10.0) * DAY for i in range(21)]
        budget: float = expected_dv * 1.5

        fastest: TransferSolution = planner.plan_transfer(
            origin="Earth", target="Mars",
            departure_times=departures,
            flight_times=flight_times,
            objective=Objective.MIN_TIME,
            delta_v_budget_km_s=budget,
        )
        cheapest: TransferSolution = planner.plan_transfer(
            origin="Earth", target="Mars",
            departure_times=departures,
            flight_times=flight_times,
            objective=Objective.MIN_DELTA_V,
        )
        assert fastest.total_delta_v <= budget
        assert fastest.arrival_time <= cheapest.arrival_time

    def test_min_time_requires_budget(self, planner: MissionPlanner) -> None:
        with pytest.raises(ValueError):
            planner.plan_transfer(origin="Earth", target="Mars",
                                  departure_times=[0.0],
                                  flight_times=[250.0 * DAY],
                                  objective=Objective.MIN_TIME)

    def test_empty_window_raises(self, planner: MissionPlanner) -> None:
        with pytest.raises(LambertNoConvergence):
            planner.plan_transfer(origin="Earth", target="Mars",
                                  departure_times=[0.0],
                                  flight_times=[60.0],  # infeasible
                                  objective=Objective.MIN_DELTA_V)


class TestPorkchop:
    def test_grid_has_all_points(self, planner: MissionPlanner) -> None:
        departures = [0.0, 10.0 * DAY]
        flight_times = [200.0 * DAY, 250.0 * DAY, 300.0 * DAY]
        grid = planner.porkchop(origin="Earth", target="Mars",
                                departure_times=departures,
                                flight_times=flight_times)
        assert len(grid) == 6
        assert all(p.total_delta_v is None or p.total_delta_v > 0.0 for p in grid)


class TestToFlightPlan:
    def test_plan_structure(self, planner: MissionPlanner) -> None:
        solution = planner.evaluate_transfer(origin="Earth", target="Mars",
                                             departure_time=0.0,
                                             time_of_flight=250.0 * DAY)
        assert solution is not None
        plan = planner.to_flight_plan(solution, burn_duration=600.0)

        assert len(plan.instructions) == 3
        depart, coast, arrive = plan.instructions
        assert isinstance(depart, VectorBurnInstruction)
        assert isinstance(coast, CoastInstruction)
        assert isinstance(arrive, VectorBurnInstruction)
        # Burns reproduce the Lambert delta-v vectors exactly.
        assert depart.direction == solution.departure_delta_v.normalized()
        assert arrive.direction == solution.arrival_delta_v.normalized()
        # Total plan duration adds up to the time of flight.
        total_duration: float = sum(i.duration for i in plan.instructions)
        assert total_duration == pytest.approx(250.0 * DAY)

    def test_burn_duration_must_fit(self, planner: MissionPlanner) -> None:
        solution = planner.evaluate_transfer(origin="Earth", target="Mars",
                                             departure_time=0.0,
                                             time_of_flight=250.0 * DAY)
        assert solution is not None
        with pytest.raises(ValueError):
            planner.to_flight_plan(solution, burn_duration=130.0 * DAY)

    def test_orbit_insertion_plan_structure(self, planner: MissionPlanner) -> None:
        solution = planner.evaluate_transfer(origin="Earth", target="Mars",
                                             departure_time=0.0,
                                             time_of_flight=250.0 * DAY)
        assert solution is not None
        plan = planner.to_flight_plan(solution, burn_duration=600.0,
                                      orbit_insertion=True,
                                      insertion_altitude_km=400.0)

        # Departure burn, coast, then a reactive insertion (no match burn).
        assert len(plan.instructions) == 3
        depart, coast, insertion = plan.instructions
        assert isinstance(depart, VectorBurnInstruction)
        assert isinstance(coast, CoastInstruction)
        assert isinstance(insertion, OrbitInsertionInstruction)
        assert depart.direction == solution.departure_delta_v.normalized()
        assert insertion.target_body == "Mars"
        assert insertion.target_altitude_km == 400.0
        # Coast ends before nominal arrival so insertion is active early.
        assert coast.duration < solution.time_of_flight - 600.0
