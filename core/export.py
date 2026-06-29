"""
Trajectory export.

Dumps a spaceship's recorded history — position, velocity, mass, fuel and
thrust at every step — to CSV or JSON, so a flight can be reconstructed or
analysed elsewhere (plotted, diffed against a reference ephemeris, etc.).

The history holds one snapshot per *display* step, so the export's time
resolution matches the cadence the flight was stepped at. Each snapshot
stores the `time_step` that produced it; cumulative time is built from those
(offset by `start_time_s`, e.g. a mission's departure time, so the exported
`time_s` can be absolute simulation time).

This module is pure (no GUI): it reads a `Spaceship`'s public state.
"""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.spaceship import Spaceship, StateSnapshot

FIELDNAMES: list[str] = [
    "time_s",
    "x_km", "y_km", "z_km",
    "vx_km_s", "vy_km_s", "vz_km_s",
    "mass_kg", "main_fuel_kg",
    "throttle",
    "thrust_x", "thrust_y", "thrust_z",
    "ax_km_s2", "ay_km_s2", "az_km_s2",
]


def _total_mass(ship: Spaceship, snapshot: StateSnapshot) -> float:
    """Total mass at a snapshot from the ship's constants + recorded fuel."""
    mass: float = ship.structure_mass + ship.payload_mass + snapshot.main_fuel_mass
    if not snapshot.takeoff_jettisoned and ship.takeoff_propulsion is not None:
        mass += ship.takeoff_propulsion.structure_mass + snapshot.takeoff_fuel_mass
    return mass


def trajectory_rows(ship: Spaceship, start_time_s: float = 0.0) -> list[dict[str, float]]:
    """One dict of state per recorded step, with cumulative `time_s`."""
    rows: list[dict[str, float]] = []
    time_s: float = start_time_s
    for index, snapshot in enumerate(ship.history):
        if index > 0:
            time_s += snapshot.time_step
        rows.append({
            "time_s": time_s,
            "x_km": snapshot.position.x,
            "y_km": snapshot.position.y,
            "z_km": snapshot.position.z,
            "vx_km_s": snapshot.velocity.x,
            "vy_km_s": snapshot.velocity.y,
            "vz_km_s": snapshot.velocity.z,
            "mass_kg": _total_mass(ship, snapshot),
            "main_fuel_kg": snapshot.main_fuel_mass,
            "throttle": snapshot.throttle,
            "thrust_x": snapshot.thrust_direction.x,
            "thrust_y": snapshot.thrust_direction.y,
            "thrust_z": snapshot.thrust_direction.z,
            "ax_km_s2": snapshot.acceleration.x,
            "ay_km_s2": snapshot.acceleration.y,
            "az_km_s2": snapshot.acceleration.z,
        })
    return rows


def export_csv(ship: Spaceship, path: str, start_time_s: float = 0.0) -> int:
    """Write the trajectory as CSV. Returns the number of rows written."""
    rows = trajectory_rows(ship, start_time_s)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_json(ship: Spaceship, path: str, start_time_s: float = 0.0,
                metadata: dict[str, Any] | None = None) -> int:
    """Write the trajectory as JSON (`metadata` + `states`). Returns row count."""
    rows = trajectory_rows(ship, start_time_s)
    document: dict[str, Any] = {"metadata": metadata or {}, "states": rows}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
    return len(rows)
