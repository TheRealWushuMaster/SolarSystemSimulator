"""Renderer-only tuning for the Ursina desktop app. Settings shared with the
web backend (EPHEMERIS_FILE, simulation_steps, ORBIT_SAMPLES) live in the
top-level config.py instead."""

from __future__ import annotations
import os

_ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Surface textures (equirectangular maps from Solar System Scope, CC BY 4.0).
# Drop the 2k JPGs/PNG into TEXTURE_DIR (see textures/README.md); any that
# are missing fall back to the body's flat colour. There is no Solar System
# Scope map for Pluto, so it stays a coloured sphere.
TEXTURE_DIR: str = os.path.join(_ROOT_DIR, "textures")
EXPORT_DIR: str = os.path.join(_ROOT_DIR, "exports")
MISSIONS_FILE: str = os.path.join(_ROOT_DIR, "data", "missions.json")
SATURN_RING_TEXTURE: str = "2k_saturn_ring_alpha.png"

# A historical-mission camera zoom wide enough to take in the outer planets.
HISTORICAL_CAMERA_Z: float = -200.0

# A custom (not-real) Earth -> Moon Hohmann trip, offered in the mission menu.
MOON_TRIP_NAME: str = "Earth-Moon trip"
MOON_PARKING_ALTITUDE_KM: float = 500.0

POSITION_SCALE: float = 1e-7        # ursina units per km (1 unit = 1e7 km)
RING_SEGMENTS: int = 64             # segments per planetary ring
DEFAULT_TIME_STEP_INDEX: int = 7    # "1 day"
DEFAULT_CAMERA_Z: float = -60.0     # starting / reset zoom
DEFAULT_CAMERA_PITCH: float = 30.0  # starting / reset tilt

# Near clip must be tiny so bodies don't vanish when zoomed in close
# (Ursina's default of 0.1 clips anything nearer than that).
CAMERA_NEAR_CLIP: float = 0.001
CAMERA_FAR_CLIP: float = 10000.0

# Marker / label apparent sizes. The marker fraction of camera distance
# gives a dot of ~2-3 px radius at the default field of view.
MARKER_APPARENT_SIZE: float = 0.004
LABEL_VERTICAL_OFFSET: float = 0.03
LABEL_NUDGE_STEP: float = 0.035     # vertical step when de-overlapping
LABEL_NUDGE_ATTEMPTS: int = 4       # tries above/below before giving up

# The single craft entity. When idle it sits in a (kinematic) parking
# orbit around its home body; a FLY_TO target replaces it with a real,
# simulated mission craft.
SHIP_NAME: str = "Ship"
SHIP_RADIUS_KM: float = 1.0          # rendered like a tiny body (marker dot)
DEFAULT_HOME_BODY: str = "Earth"     # where the craft starts / departs from
PARKING_ALTITUDE_KM: float = 2000.0  # parking-orbit altitude above the home body

# FLY_TO mission planning.
INSERTION_ALTITUDE_KM: float = 500.0
# Finer fixed step (5 min) so the fast arrival flyby and capture are
# resolved without overshooting; the cruise is cheap at this size too.
MISSION_SHIP_MAX_DT: float = 300.0
GRID_DEPARTURE_SAMPLES: int = 24     # porkchop grid resolution
GRID_FLIGHT_SAMPLES: int = 12
MAX_DEPARTURE_WINDOW_S: float = 3.0 * 365.25 * 86400.0   # cap the search span

# Mid-course corrections: fractions of the way (in time) through the
# transfer at which to re-solve Lambert from the live state and burn the
# correction, so the craft actually arrives where the moving target is.
MCC_FRACTIONS: tuple[float, ...] = (0.5, 0.8, 0.93)
MIN_MCC_LEAD_S: float = 3.0 * 86400.0   # skip corrections inside this of arrival
