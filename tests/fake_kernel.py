"""
A stand-in for `jplephem.spk.SPK`, so server tests can build a whole
`SolaraSession` without the 146MB de440t.bsp (which is gitignored and absent
in CI).

The real kernel stores Chebyshev polynomials per segment; this returns simple
linear motion instead -- `position = base + rate * (jd - epoch_jd)`, matching
jplephem's `compute_and_differentiate` contract (position km, velocity
km/day). That is enough for every server-level behaviour under test: session
wiring, command dispatch, and serialization all care that states are
*distinct and finite*, not that they are astronomically correct. Anything
that depends on real orbital geometry (Lambert windows, the Moon transfer)
is deliberately not exercised against this fake.

The segment table covers exactly the SPICE chains in data/bodies.json.
Magnitudes are only roughly plausible -- barycentre-relative segments are
~1e8 km, body-relative ones ~1e5 km -- so distances and radii stay in
sensible ranges without pretending to be an ephemeris.
"""

from __future__ import annotations

from dataclasses import dataclass

# Arbitrary but fixed reference epoch (J2000-ish); tests that care about
# absolute dates pass this to SolaraSession's ephemeris directly.
FAKE_EPOCH_JD: float = 2460000.5

# (origin, target) -> (base position km, rate km/day). Covers every chain in
# data/bodies.json: Sun [0,10], the planets [0,N] (+ [N,N99] for the inner
# three), Earth [0,3,399] and the Moon [0,3,301].
_SEGMENTS: dict[tuple[int, int], tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    (0, 10): ((1.0e6, 0.0, 0.0), (1.0, 0.0, 0.0)),              # Sun vs SSB
    (0, 1): ((5.8e7, 1.0e6, 0.0), (0.0, 4.1e6, 0.0)),           # Mercury barycentre
    (1, 199): ((1.0e3, 0.0, 0.0), (0.0, 1.0e2, 0.0)),
    (0, 2): ((1.08e8, 2.0e6, 0.0), (0.0, 3.0e6, 0.0)),          # Venus barycentre
    (2, 299): ((1.0e3, 0.0, 0.0), (0.0, 1.0e2, 0.0)),
    (0, 3): ((1.5e8, 3.0e6, 0.0), (0.0, 2.6e6, 0.0)),           # Earth-Moon barycentre
    (3, 399): ((-4.7e3, 0.0, 0.0), (0.0, -9.0e4, 0.0)),         # Earth vs EMB
    (3, 301): ((3.8e5, 0.0, 0.0), (0.0, 7.3e6, 0.0)),           # Moon vs EMB
    (0, 4): ((2.28e8, 4.0e6, 0.0), (0.0, 2.1e6, 0.0)),          # Mars
    (0, 5): ((7.78e8, 5.0e6, 0.0), (0.0, 1.1e6, 0.0)),          # Jupiter
    (0, 6): ((1.43e9, 6.0e6, 0.0), (0.0, 8.4e5, 0.0)),          # Saturn
    (0, 7): ((2.87e9, 7.0e6, 0.0), (0.0, 5.9e5, 0.0)),          # Uranus
    (0, 8): ((4.50e9, 8.0e6, 0.0), (0.0, 4.7e5, 0.0)),          # Neptune
    (0, 9): ((5.91e9, 9.0e6, 0.0), (0.0, 4.1e5, 0.0)),          # Pluto
}


@dataclass(slots=True, frozen=True)
class FakeSpkSegment:
    """One linear-motion segment, shaped like jplephem's segment interface."""

    base: tuple[float, float, float]
    rate: tuple[float, float, float]     # km/day
    epoch_jd: float

    def compute_and_differentiate(self, tdb: float) -> tuple[tuple[float, float, float],
                                                             tuple[float, float, float]]:
        """Return (position km, velocity km/day) at Julian date `tdb`."""
        elapsed_days: float = tdb - self.epoch_jd
        position: tuple[float, float, float] = (
            self.base[0] + self.rate[0] * elapsed_days,
            self.base[1] + self.rate[1] * elapsed_days,
            self.base[2] + self.rate[2] * elapsed_days,
        )
        return position, self.rate


class FakeSpkKernel:
    """
    Dict-backed stand-in for `jplephem.spk.SPK`.

    Unknown segments fall back to a generic one rather than raising, so a
    session can be built even if data/bodies.json gains a body before this
    table is updated -- a missing chain should not fail an unrelated test.
    """

    def __init__(self, epoch_jd: float = FAKE_EPOCH_JD) -> None:
        self.epoch_jd: float = epoch_jd
        self.requested_keys: list[tuple[int, int]] = []

    def __getitem__(self, key: tuple[int, int]) -> FakeSpkSegment:
        self.requested_keys.append(key)
        base, rate = _SEGMENTS.get(key, ((1.0e8, 1.0e7, 0.0), (0.0, 1.0e6, 0.0)))
        return FakeSpkSegment(base=base,
                              rate=rate,
                              epoch_jd=self.epoch_jd)
