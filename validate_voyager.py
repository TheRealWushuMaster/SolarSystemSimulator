"""
Voyager 1 Jupiter-flyby validation.

Loads Voyager 1's *real* heliocentric state at 1977-09-15 (from JPL HORIZONS,
saved in data/voyager1_horizons.txt) and lets Solara's N-body integrator fly
it — coasting, no thrust — through the 1979-03-05 Jupiter gravity assist.
The simulated trajectory is then compared against HORIZONS' record of where
Voyager actually was.

Everything is in the same frame Solara already uses (heliocentric ICRF),
which was confirmed to match HORIZONS to 0 km, so the state vector drops
straight in. Run with the project venv:

    .venv\\Scripts\\python.exe validate_voyager.py
"""



from __future__ import annotations
import os
import re
from typing import Any
from jplephem.spk import SPK
from core.ephemeris import JplEphemeris
from core.flight_plan import FlightPlan
from core.spaceship import PropulsionSystem, Spaceship
from core.vec3 import Vec3
from creators import load_bodies_from_json
from settings import EPHEMERIS_FILE

HORIZONS_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "data", "voyager1_horizons.txt")

# Adaptive step: move at most this fraction of the distance to the nearest
# planet per step, clamped — tiny through the flyby, big in cruise.
STEP_FRACTION: float = 0.005
DT_MIN: float = 30.0          # s
DT_MAX: float = 43200.0       # s (12 h)

_FLOAT: re.Pattern[str] = re.compile(r"[-+]?\d+\.\d+E[-+]?\d+")

def parse_horizons(path: str) -> list[tuple[float, Vec3, Vec3]]:
    """Parse a HORIZONS VECTORS table into (JD_TDB, position, velocity) rows."""
    text: str = open(file=path,
                     encoding="utf-8").read()
    block: list[str] = text.split(sep="$$SOE",
                                  maxsplit=1)[1].split(sep="$$EOE",
                                              maxsplit=1)[0].strip().splitlines()
    rows: list[tuple[float, Vec3, Vec3]] = []
    for i in range(0, len(block), 3):
        jd: float = float(block[i].split(sep="=",
                                         maxsplit=1)[0])
        x, y, z = (float(v) for v in _FLOAT.findall(block[i + 1]))
        vx, vy, vz = (float(v) for v in _FLOAT.findall(block[i + 2]))
        rows.append((jd, Vec3(x, y, z), Vec3(x=vx,
                                             y=vy,
                                             z=vz)))
    return rows

def adaptive_dt(ship: Spaceship, bodies: dict) -> float:
    nearest_distance: float = float("inf")
    nearest = None
    for name, body in bodies.items():
        if name == "Sun":
            continue
        distance = (ship.position - body.position).magnitude()
        if distance < nearest_distance:
            nearest_distance, nearest = distance, body
    relative_speed = (ship.velocity - nearest.velocity).magnitude()
    dt: float = STEP_FRACTION * nearest_distance / max(relative_speed, 1.0)
    return max(DT_MIN, min(DT_MAX, dt))

def sync_bodies(ephemeris: JplEphemeris, bodies: dict, time_s: float) -> None:
    for name, body in bodies.items():
        position, velocity = ephemeris.state(name, time_s)
        body.position = position
        body.velocity = velocity

def main() -> None:
    if not os.path.exists(EPHEMERIS_FILE):
        print("Ephemeris kernel missing; cannot run.")
        return
    rows: list[tuple[float, Vec3, Vec3]] = parse_horizons(path=HORIZONS_FILE)
    jd0, position0, velocity0 = rows[0]
    reference: list[tuple[float, Vec3]] = [((jd - jd0) * 86400.0, pos)
                                           for jd, pos, _ in rows]

    kernel = SPK.open(EPHEMERIS_FILE)
    bodies = load_bodies_from_json()
    ephemeris: JplEphemeris = JplEphemeris.from_bodies(kernel=kernel,
                                                       bodies=bodies,
                                                       epoch_jd=jd0)
    ship: Spaceship = Spaceship(structure_mass=825.0,
                                payload_mass=0.0,
                                main_propulsion=PropulsionSystem(),     # inert: coasts
                                initial_position=position0,
                                initial_velocity=velocity0,
                                flight_plan=FlightPlan(),
                                max_integration_dt=DT_MAX)
    print(f"Voyager 1 from HORIZONS state at JD {jd0} (1977-09-15)")
    print(f"  start: r={position0.magnitude()/1.495978707e8:.3f} AU, " +
          f"v={velocity0.magnitude():.3f} km/s\n")
    print(f"{'date (days)':>11} | {'pos error':>12} | {'helio speed':>11} | " +
          f"{'dist to Jupiter':>16}")
    print("-" * 60)
    closest_jupiter: float = float("inf")
    closest_time: float = 0.0
    time_s: float = 0.0
    end_time: float = reference[-1][0]
    next_index = 1
    while next_index < len(reference) and time_s < end_time:
        sync_bodies(ephemeris, bodies, time_s)
        dt: float = min(adaptive_dt(ship, bodies), reference[next_index][0] - time_s)
        ship.step_forward(dt, bodies)
        time_s += dt
        jupiter_distance = (ship.position - bodies["Jupiter"].position).magnitude()
        if jupiter_distance < closest_jupiter:
            closest_jupiter, closest_time = jupiter_distance, time_s
        if time_s >= reference[next_index][0] - 1e-3:
            ref_time, ref_pos = reference[next_index]
            error: float = (ship.position - ref_pos).magnitude()
            if next_index % 5 == 0 or next_index == len(reference) - 1:
                print(f"{ref_time/86400.0:11.0f} | {error:9.0f} km | " +
                      f"{ship.velocity.magnitude():8.3f} km/s | " +
                      f"{jupiter_distance/1e6:12.3f} Mkm")
            next_index += 1
    jupiter_radii: float | Any = closest_jupiter / 71492.0
    print("\n--- Jupiter encounter ---")
    print(f"  simulated closest approach: {closest_jupiter:,.0f} km " +
          f"({jupiter_radii:.2f} Jupiter radii) at day {closest_time/86400.0:.1f} " +
          f"(JD {jd0 + closest_time/86400.0:.1f})")
    print(f"  real Voyager 1 closest approach: ~348,890 km (4.88 R_J) on 1979-03-05")
    kernel.close()



if __name__ == "__main__":
    main()
