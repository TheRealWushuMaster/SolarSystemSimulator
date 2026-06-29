from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from core.ephemeris import SECONDS_PER_DAY, JplEphemeris
from core.vec3 import Vec3

EPOCH_JD: float = 2460000.5


@dataclass
class FakeSegment:
    """
    A linear-motion SPK segment: position = base + rate * (jd - epoch).
    Mimics jplephem's compute_and_differentiate (velocity in km/day).
    """
    base: tuple[float, float, float]
    rate: tuple[float, float, float]  # km/day

    def compute_and_differentiate(self, tdb: float) -> tuple:
        dt: float = tdb - EPOCH_JD
        position = tuple(b + r * dt for b, r in zip(self.base, self.rate))
        return position, self.rate


class FakeKernel:
    """Dict-backed stand-in for jplephem.spk.SPK."""

    def __init__(self, segments: dict[tuple[int, int], FakeSegment]) -> None:
        self.segments = segments

    def __getitem__(self, key: tuple[int, int]) -> FakeSegment:
        return self.segments[key]


@pytest.fixture
def fake_kernel() -> FakeKernel:
    return FakeKernel(segments={
        # Sun 1000 km from the SSB, drifting +x at 1 km/day.
        (0, 10): FakeSegment(base=(1000.0, 0.0, 0.0), rate=(1.0, 0.0, 0.0)),
        # Earth-Moon barycenter relative to SSB.
        (0, 3): FakeSegment(base=(1.5e8, 0.0, 0.0), rate=(0.0, 2.5e6, 0.0)),
        # Earth relative to the EMB.
        (3, 399): FakeSegment(base=(-4000.0, 0.0, 0.0), rate=(0.0, -90000.0, 0.0)),
    })


@pytest.fixture
def location_paths() -> dict[str, list[int]]:
    return {"Sun": [0, 10], "Earth": [0, 3, 399]}


class TestChainWalking:
    def test_single_segment_body(self, fake_kernel: FakeKernel,
                                 location_paths: dict[str, list[int]]) -> None:
        ephemeris = JplEphemeris(kernel=fake_kernel,
                                 location_paths=location_paths,
                                 epoch_jd=EPOCH_JD,
                                 center=None)
        position, velocity = ephemeris.state("Sun", time_s=0.0)
        assert position == Vec3(1000.0, 0.0, 0.0)
        # 1 km/day -> km/s
        assert velocity.x == pytest.approx(1.0 / SECONDS_PER_DAY)

    def test_chained_segments_sum(self, fake_kernel: FakeKernel,
                                  location_paths: dict[str, list[int]]) -> None:
        """Earth = (SSB->EMB) + (EMB->Earth)."""
        ephemeris = JplEphemeris(kernel=fake_kernel,
                                 location_paths=location_paths,
                                 epoch_jd=EPOCH_JD,
                                 center=None)
        position, velocity = ephemeris.state("Earth", time_s=0.0)
        assert position == Vec3(1.5e8 - 4000.0, 0.0, 0.0)
        assert velocity.y == pytest.approx((2.5e6 - 90000.0) / SECONDS_PER_DAY)

    def test_time_seconds_to_julian_date(self, fake_kernel: FakeKernel,
                                         location_paths: dict[str, list[int]]) -> None:
        """One day in seconds must advance the kernel by one JD."""
        ephemeris = JplEphemeris(kernel=fake_kernel,
                                 location_paths=location_paths,
                                 epoch_jd=EPOCH_JD,
                                 center=None)
        position, _ = ephemeris.state("Sun", time_s=SECONDS_PER_DAY)
        assert position.x == pytest.approx(1001.0)  # 1000 + 1 km/day * 1 day


class TestCenterSubtraction:
    def test_heliocentric_by_default(self, fake_kernel: FakeKernel,
                                     location_paths: dict[str, list[int]]) -> None:
        ephemeris = JplEphemeris(kernel=fake_kernel,
                                 location_paths=location_paths,
                                 epoch_jd=EPOCH_JD)
        position, _ = ephemeris.state("Earth", time_s=0.0)
        # SSB-relative Earth x minus SSB-relative Sun x.
        assert position.x == pytest.approx(1.5e8 - 4000.0 - 1000.0)

    def test_center_relative_to_itself_is_zero(self, fake_kernel: FakeKernel,
                                               location_paths: dict[str, list[int]]) -> None:
        ephemeris = JplEphemeris(kernel=fake_kernel,
                                 location_paths=location_paths,
                                 epoch_jd=EPOCH_JD)
        position, velocity = ephemeris.state("Sun", time_s=0.0)
        assert position == Vec3()
        assert velocity == Vec3()


class TestValidation:
    def test_unknown_body_raises(self, fake_kernel: FakeKernel,
                                 location_paths: dict[str, list[int]]) -> None:
        ephemeris = JplEphemeris(kernel=fake_kernel,
                                 location_paths=location_paths,
                                 epoch_jd=EPOCH_JD)
        with pytest.raises(KeyError):
            ephemeris.state("Vulcan", time_s=0.0)

    def test_short_location_path_rejected(self, fake_kernel: FakeKernel) -> None:
        with pytest.raises(ValueError):
            JplEphemeris(kernel=fake_kernel,
                         location_paths={"Sun": [10]},
                         epoch_jd=EPOCH_JD,
                         center=None)

    def test_center_must_have_path(self, fake_kernel: FakeKernel) -> None:
        with pytest.raises(ValueError):
            JplEphemeris(kernel=fake_kernel,
                         location_paths={"Earth": [0, 3, 399]},
                         epoch_jd=EPOCH_JD,
                         center="Sun")

    def test_from_bodies_builder(self, fake_kernel: FakeKernel) -> None:
        from creators import load_bodies_from_json
        bodies = load_bodies_from_json()
        # Restrict to bodies whose segments the fake kernel provides.
        subset = {name: bodies[name] for name in ("Sun", "Earth")}
        ephemeris = JplEphemeris.from_bodies(kernel=fake_kernel,
                                             bodies=subset,
                                             epoch_jd=EPOCH_JD)
        position, _ = ephemeris.state("Earth", time_s=0.0)
        assert position.x == pytest.approx(1.5e8 - 4000.0 - 1000.0)


# ----------------------------------------------------------------------
# Integration with the real JPL kernel (skipped if not downloaded)
# ----------------------------------------------------------------------

_KERNEL_PATH = Path(__file__).parent.parent / "de440t.bsp"

requires_kernel = pytest.mark.skipif(
    not _KERNEL_PATH.exists(),
    reason="de440t.bsp not downloaded (run the app once to fetch it)",
)


@requires_kernel
class TestRealKernel:
    @pytest.fixture
    def real_ephemeris(self) -> JplEphemeris:
        from jplephem.spk import SPK
        from creators import load_bodies_from_json
        kernel = SPK.open(str(_KERNEL_PATH))
        bodies = load_bodies_from_json()
        # J2000.0 epoch
        return JplEphemeris.from_bodies(kernel=kernel,
                                        bodies=bodies,
                                        epoch_jd=2451545.0)

    def test_earth_distance_is_one_au(self, real_ephemeris: JplEphemeris) -> None:
        au_km: float = 1.495978707e8
        position, _ = real_ephemeris.state("Earth", time_s=0.0)
        assert position.magnitude() == pytest.approx(au_km, rel=0.02)

    def test_earth_speed_is_29_8_km_s(self, real_ephemeris: JplEphemeris) -> None:
        _, velocity = real_ephemeris.state("Earth", time_s=0.0)
        assert velocity.magnitude() == pytest.approx(29.78, rel=0.02)

    def test_earth_returns_after_one_year(self, real_ephemeris: JplEphemeris) -> None:
        year_s: float = 365.2563 * SECONDS_PER_DAY
        start, _ = real_ephemeris.state("Earth", time_s=0.0)
        end, _ = real_ephemeris.state("Earth", time_s=year_s)
        drift: float = (end - start).magnitude()
        assert drift < 0.05 * start.magnitude()

    def test_planner_end_to_end_with_real_data(self, real_ephemeris: JplEphemeris) -> None:
        """The full chain: real ephemeris -> porkchop search -> plan."""
        from core.mission_planner import MissionPlanner, Objective
        DAY: float = SECONDS_PER_DAY
        planner = MissionPlanner(ephemeris=real_ephemeris)
        best = planner.plan_transfer(
            origin="Earth", target="Mars",
            departure_times=[i * 20.0 * DAY for i in range(40)],
            flight_times=[(150.0 + i * 20.0) * DAY for i in range(11)],
            objective=Objective.MIN_DELTA_V,
        )
        # Real-world Earth->Mars transfers run roughly 5.5-7 km/s
        # total depending on the window; sanity-bound it.
        assert 4.0 < best.total_delta_v < 9.0
        plan = planner.to_flight_plan(best)
        assert len(plan.instructions) == 3
