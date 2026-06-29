"""Historical mission catalogue tests."""

from __future__ import annotations

import json
import os

from core.missions import HistoricalMission, load_missions
from core.vec3 import Vec3

CATALOGUE = os.path.join(os.path.dirname(__file__), "..", "data", "missions.json")


def test_catalogue_loads_voyagers() -> None:
    missions = load_missions(CATALOGUE)
    assert "Voyager 1" in missions
    assert "Voyager 2" in missions
    v1 = missions["Voyager 1"]
    assert isinstance(v1, HistoricalMission)
    assert v1.epoch_jd == 2443401.5
    assert isinstance(v1.position, Vec3) and isinstance(v1.velocity, Vec3)
    # Launch-era state: ~1 AU from the Sun, ~40 km/s.
    assert 1.4e8 < v1.position.magnitude() < 1.6e8
    assert 35.0 < v1.velocity.magnitude() < 45.0


def test_defaults_fill_in(tmp_path) -> None:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({
        "Probe": {"epoch_jd": 2451545.0,
                  "position_km": [1.0, 2.0, 3.0],
                  "velocity_km_s": [0.1, 0.2, 0.3]}
    }), encoding="utf-8")
    missions = load_missions(str(path))
    probe = missions["Probe"]
    assert probe.position == Vec3(1.0, 2.0, 3.0)
    assert probe.follow == "Sun"          # default
    assert probe.structure_mass == 1000.0  # default
