from __future__ import annotations

from math import pi, sqrt

import pytest

from core.lambert import LambertNoConvergence, solve_lambert
from core.vec3 import Vec3

MU_EARTH: float = 398600.0  # km^3/s^2


class TestLambertTextbookCase:
    def test_curtis_example_5_2(self) -> None:
        """
        Validation against Curtis, 'Orbital Mechanics for Engineering
        Students', Example 5.2: a 1-hour Earth-orbit transfer with a
        published solution to check against.
        """
        r1 = Vec3(5000.0, 10000.0, 2100.0)
        r2 = Vec3(-14600.0, 2500.0, 7000.0)
        solution = solve_lambert(r1=r1, r2=r2,
                                 time_of_flight=3600.0,
                                 mu=MU_EARTH)
        assert solution.v1.x == pytest.approx(-5.9925, abs=1e-3)
        assert solution.v1.y == pytest.approx(1.9254, abs=1e-3)
        assert solution.v1.z == pytest.approx(3.2456, abs=1e-3)
        assert solution.v2.x == pytest.approx(-3.3125, abs=1e-3)
        assert solution.v2.y == pytest.approx(-4.1966, abs=1e-3)
        assert solution.v2.z == pytest.approx(-0.38529, abs=1e-3)


class TestLambertCircularOrbit:
    def test_quarter_orbit_recovers_circular_velocity(self) -> None:
        """
        Two points a quarter-orbit apart on a circular orbit, with a
        quarter-period time of flight, must be connected by... that
        same circular orbit. So v1 must be the circular velocity.
        """
        radius: float = 7000.0  # km
        v_circular: float = sqrt(MU_EARTH / radius)
        quarter_period: float = (2.0 * pi * sqrt(radius**3 / MU_EARTH)) / 4.0

        r1 = Vec3(radius, 0.0, 0.0)
        r2 = Vec3(0.0, radius, 0.0)
        solution = solve_lambert(r1=r1, r2=r2,
                                 time_of_flight=quarter_period,
                                 mu=MU_EARTH)
        assert solution.v1.x == pytest.approx(0.0, abs=1e-6)
        assert solution.v1.y == pytest.approx(v_circular, rel=1e-6)
        assert solution.v1.z == pytest.approx(0.0, abs=1e-6)
        # Arrival velocity is the circular velocity rotated 90 degrees.
        assert solution.v2.x == pytest.approx(-v_circular, rel=1e-6)
        assert solution.v2.y == pytest.approx(0.0, abs=1e-6)


class TestLambertEdgeCases:
    def test_rejects_non_positive_time(self) -> None:
        with pytest.raises(ValueError):
            solve_lambert(r1=Vec3(7000.0, 0.0, 0.0),
                          r2=Vec3(0.0, 7000.0, 0.0),
                          time_of_flight=0.0,
                          mu=MU_EARTH)

    def test_rejects_zero_position(self) -> None:
        with pytest.raises(ValueError):
            solve_lambert(r1=Vec3(),
                          r2=Vec3(0.0, 7000.0, 0.0),
                          time_of_flight=3600.0,
                          mu=MU_EARTH)

    def test_degenerate_180_degree_transfer(self) -> None:
        """Diametrically opposite points leave the plane undefined."""
        with pytest.raises(LambertNoConvergence):
            solve_lambert(r1=Vec3(7000.0, 0.0, 0.0),
                          r2=Vec3(-7000.0, 0.0, 0.0),
                          time_of_flight=3600.0,
                          mu=MU_EARTH)

    def test_impossibly_short_time_raises(self) -> None:
        """No orbit can cover interplanetary distance in one minute."""
        with pytest.raises(LambertNoConvergence):
            solve_lambert(r1=Vec3(1.496e8, 0.0, 0.0),
                          r2=Vec3(0.0, 2.28e8, 0.0),
                          time_of_flight=60.0)
