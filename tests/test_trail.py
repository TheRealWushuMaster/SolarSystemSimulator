from __future__ import annotations

import pytest

from core.trail import TrailPath
from core.vec3 import Vec3


class TestConstruction:
    def test_rejects_non_positive_separation(self) -> None:
        with pytest.raises(ValueError):
            TrailPath(min_separation_km=0.0)

    def test_rejects_tiny_cap(self) -> None:
        with pytest.raises(ValueError):
            TrailPath(min_separation_km=1.0, max_points=1)


class TestDecimation:
    def test_first_point_always_added(self) -> None:
        trail = TrailPath(min_separation_km=100.0)
        assert trail.add(Vec3(0.0, 0.0, 0.0)) is True
        assert len(trail) == 1

    def test_point_too_close_is_skipped(self) -> None:
        trail = TrailPath(min_separation_km=100.0)
        trail.add(Vec3(0.0, 0.0, 0.0))
        assert trail.add(Vec3(50.0, 0.0, 0.0)) is False
        assert len(trail) == 1

    def test_point_far_enough_is_added(self) -> None:
        trail = TrailPath(min_separation_km=100.0)
        trail.add(Vec3(0.0, 0.0, 0.0))
        assert trail.add(Vec3(150.0, 0.0, 0.0)) is True
        assert len(trail) == 2

    def test_separation_measured_from_last_recorded(self) -> None:
        """Skipped points must not reset the reference point."""
        trail = TrailPath(min_separation_km=100.0)
        trail.add(Vec3(0.0, 0.0, 0.0))
        trail.add(Vec3(60.0, 0.0, 0.0))   # skipped, < 100 from origin
        # 60 -> 120 is only 60, but 0 -> 120 is 120, so it should add.
        assert trail.add(Vec3(120.0, 0.0, 0.0)) is True
        assert len(trail) == 2

    def test_exact_threshold_is_added(self) -> None:
        trail = TrailPath(min_separation_km=100.0)
        trail.add(Vec3(0.0, 0.0, 0.0))
        assert trail.add(Vec3(100.0, 0.0, 0.0)) is True


class TestRingBuffer:
    def test_cap_drops_oldest(self) -> None:
        trail = TrailPath(min_separation_km=1.0, max_points=3)
        for x in range(5):
            trail.add(Vec3(float(x) * 10.0, 0.0, 0.0))
        assert len(trail) == 3
        # Oldest two (x=0, x=10) dropped; newest three remain.
        assert trail.points[0] == Vec3(20.0, 0.0, 0.0)
        assert trail.points[-1] == Vec3(40.0, 0.0, 0.0)

    def test_uncapped_grows_freely(self) -> None:
        trail = TrailPath(min_separation_km=1.0)
        for x in range(100):
            trail.add(Vec3(float(x) * 10.0, 0.0, 0.0))
        assert len(trail) == 100


class TestClear:
    def test_clear_empties(self) -> None:
        trail = TrailPath(min_separation_km=1.0)
        trail.add(Vec3(0.0, 0.0, 0.0))
        trail.add(Vec3(10.0, 0.0, 0.0))
        trail.clear()
        assert len(trail) == 0
        # After clearing, the next point is treated as the first again.
        assert trail.add(Vec3(5.0, 0.0, 0.0)) is True
