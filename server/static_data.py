"""
Static catalogue data for the web frontend.

Bodies and missions barely change (bodies.json is fixed, missions.json only
grows when a new historical mission is added), so these are reshaped once
into the wire format and served straight from data/*.json rather than
re-derived from the live per-session CelestialBody objects.
"""

from __future__ import annotations

import json
from math import pi
from pathlib import Path
from typing import Any

from config import ORBIT_SAMPLES

_DATA_DIR: Path = Path(__file__).parent.parent / "data"
_BODIES_JSON: Path = _DATA_DIR / "bodies.json"
_MISSIONS_JSON: Path = _DATA_DIR / "missions.json"


def body_catalogue() -> dict[str, dict[str, Any]]:
    """Reshape data/bodies.json into the wire format for GET /api/bodies."""
    with open(_BODIES_JSON, encoding="utf-8") as handle:
        raw: dict[str, Any] = json.load(handle)
    catalogue: dict[str, dict[str, Any]] = {}
    for name, props in raw.get("stars", {}).items():
        catalogue[name] = _body_entry(name, props, is_star=True)
    for name, props in raw.get("planets", {}).items():
        catalogue[name] = _body_entry(name, props, is_star=False)
    for name, props in raw.get("moons", {}).items():
        catalogue[name] = _body_entry(name, props, is_star=False)
    return catalogue


def _rotation_period_s(props: dict[str, Any]) -> float:
    """Seconds per rotation, mirroring core.bodies.CelestialBody.rotation_period
    (circumference / rotation_velocity, both already in km and km/s)."""
    rotation_velocity: float = props.get("rotation_velocity", 0.0)
    if rotation_velocity == 0.0:
        return 0.0
    circumference: float = 2.0 * pi * props["radius"]
    return circumference / rotation_velocity


def _body_entry(name: str, props: dict[str, Any], is_star: bool) -> dict[str, Any]:
    return {
        "radius_km": props["radius"],
        "mass_kg": props["mass"],
        "color": props.get("color", "#ffffff"),
        "rings": int(props.get("rings", 0)),
        "orbital_period_days": props["orbital_period"],
        "rotation_period_s": _rotation_period_s(props),
        "parent_body": props.get("parent_body"),
        "texture": props.get("texture"),
        "is_star": is_star,
    }


def orbit_lines(kernel: Any, epoch_jd: float) -> dict[str, list[list[float]]]:
    """
    One faint line per body that orbits the Sun directly, sampled over one
    orbital period -- mirrors app.py's _draw_orbit_lines(). Stateless: takes
    the shared, read-only SPK kernel directly rather than a session (no
    per-tick mutation involved, so it needs no session of its own).
    """
    from core.bodies import load_bodies_from_json
    from core.ephemeris import JplEphemeris

    bodies = load_bodies_from_json()
    ephemeris = JplEphemeris.from_bodies(kernel=kernel, bodies=bodies, epoch_jd=epoch_jd)
    lines: dict[str, list[list[float]]] = {}
    for name, body in bodies.items():
        if body.parent_body != "Sun" or body.orbital_period <= 0:
            continue
        period_s: float = body.orbital_period * 86400.0
        points: list[list[float]] = []
        for i in range(ORBIT_SAMPLES + 1):
            t = period_s * i / ORBIT_SAMPLES
            position, _ = ephemeris.state(name, t)
            points.append([position.x, position.y, position.z])
        lines[name] = points
    return lines


def mission_catalogue() -> dict[str, dict[str, Any]]:
    """Mission menu metadata for GET /api/missions -- no state vectors, the
    craft's actual trajectory comes from the per-tick state push once loaded."""
    with open(_MISSIONS_JSON, encoding="utf-8") as handle:
        raw: dict[str, Any] = json.load(handle)
    return {
        name: {
            "description": entry.get("description", ""),
            "color": entry.get("color", "#9fd0ff"),
            "follow": entry.get("follow", "Sun"),
        }
        for name, entry in raw.items()
    }
