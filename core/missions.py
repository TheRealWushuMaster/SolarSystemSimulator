"""
Historical mission catalogue.

A catalogue of real spacecraft the user can pick and watch fly. Each entry
holds the craft's *real* heliocentric ICRF state vector at a start epoch
(from JPL HORIZONS) plus a little display metadata. Loading one drops the
craft into the simulation at that state and lets the N-body integrator fly
it — the same coasting propagation that reproduced Voyager 1's Jupiter
encounter.

The state vectors must be in the frame Solara uses: heliocentric (Sun
body-centred) ICRF/J2000 equatorial, km and km/s — i.e. HORIZONS with
CENTER='500@10' and REF_PLANE='FRAME'.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from core.vec3 import Vec3


@dataclass(frozen=True)
class HistoricalMission:
    """One real spacecraft with its launch-era state and display metadata."""
    name: str
    epoch_jd: float          # JD (TDB) of the state vector below
    position: Vec3           # heliocentric ICRF, km
    velocity: Vec3           # heliocentric ICRF, km/s
    structure_mass: float    # kg (does not affect the trajectory)
    color: str               # "#RRGGBB" for the craft + trail
    description: str
    follow: str              # body to follow when the mission loads


def load_missions(path: str) -> dict[str, HistoricalMission]:
    """Load the mission catalogue from a JSON file."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    missions: dict[str, HistoricalMission] = {}
    for name, entry in raw.items():
        missions[name] = HistoricalMission(
            name=name,
            epoch_jd=float(entry["epoch_jd"]),
            position=Vec3(*entry["position_km"]),
            velocity=Vec3(*entry["velocity_km_s"]),
            structure_mass=float(entry.get("structure_mass", 1000.0)),
            color=entry.get("color", "#9fd0ff"),
            description=entry.get("description", ""),
            follow=entry.get("follow", "Sun"),
        )
    return missions
