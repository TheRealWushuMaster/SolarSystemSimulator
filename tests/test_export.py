"""Trajectory export tests."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field

import pytest

from core.export import export_csv, export_json, trajectory_rows, FIELDNAMES
from core.flight_plan import FlightPlan
from core.physics import circular_orbit_state
from core.spaceship import PropulsionSystem, Spaceship
from core.vec3 import Vec3

EARTH_MASS: float = 5.97e24
EARTH_RADIUS: float = 6371.0


@dataclass
class StubEarth:
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    mass: float = EARTH_MASS
    radius: float = EARTH_RADIUS


def make_ship(flight_plan: FlightPlan | None = None) -> Spaceship:
    earth = StubEarth()
    position, velocity = circular_orbit_state(earth, altitude_km=400.0)
    main = PropulsionSystem(max_thrust=100000.0, specific_impulse=300.0,
                            exhaust_velocity=4500.0, fuel_mass=4000.0)
    return Spaceship(structure_mass=2000.0, payload_mass=500.0,
                     main_propulsion=main,
                     initial_position=position, initial_velocity=velocity,
                     flight_plan=flight_plan)


def flown_ship(steps: int = 5, dt: float = 10.0) -> Spaceship:
    earth = StubEarth()
    ship = make_ship(FlightPlan().add_speed_up(throttle=1.0, duration=steps * dt))
    for _ in range(steps):
        ship.step_forward(dt=dt, bodies={"Earth": earth})
    return ship


class TestRows:
    def test_one_row_per_history_entry(self) -> None:
        ship = flown_ship(steps=5)
        rows = trajectory_rows(ship)
        assert len(rows) == len(ship.history) == 6   # initial + 5 steps

    def test_time_accumulates_from_step_sizes(self) -> None:
        ship = flown_ship(steps=4, dt=10.0)
        rows = trajectory_rows(ship, start_time_s=1000.0)
        # Initial snapshot at the offset, then +10 s each step.
        assert [r["time_s"] for r in rows] == [1000.0, 1010.0, 1020.0, 1030.0, 1040.0]

    def test_position_matches_history(self) -> None:
        ship = flown_ship(steps=3)
        rows = trajectory_rows(ship)
        last = ship.history[-1]
        assert rows[-1]["x_km"] == last.position.x
        assert rows[-1]["vy_km_s"] == last.velocity.y

    def test_mass_includes_structure_and_decreases_with_burn(self) -> None:
        ship = flown_ship(steps=5)
        rows = trajectory_rows(ship)
        dry = ship.structure_mass + ship.payload_mass
        assert rows[0]["mass_kg"] == pytest.approx(dry + 4000.0)   # full tank
        assert rows[-1]["mass_kg"] < rows[0]["mass_kg"]            # burned fuel
        assert rows[-1]["main_fuel_kg"] < 4000.0


class TestFiles:
    def test_csv_roundtrip(self, tmp_path) -> None:
        ship = flown_ship(steps=4)
        path = tmp_path / "trajectory.csv"
        count = export_csv(ship, str(path))
        assert count == len(ship.history)

        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == FIELDNAMES
            data = list(reader)
        assert len(data) == count
        assert float(data[-1]["x_km"]) == pytest.approx(ship.history[-1].position.x)

    def test_json_has_metadata_and_states(self, tmp_path) -> None:
        ship = flown_ship(steps=3)
        path = tmp_path / "trajectory.json"
        meta = {"origin": "Earth", "target": "Mars"}
        export_json(ship, str(path), start_time_s=42.0, metadata=meta)

        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["metadata"] == meta
        assert len(document["states"]) == len(ship.history)
        assert document["states"][0]["time_s"] == 42.0

    def test_coasting_ship_exports_only_initial_state(self, tmp_path) -> None:
        ship = make_ship()   # never stepped
        path = tmp_path / "t.csv"
        assert export_csv(ship, str(path)) == 1
