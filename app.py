"""
Solara — Ursina renderer.

New graphics front-end on top of the `core` package. The old Tkinter
app (GUI.py) is untouched and still runnable; this is its replacement.

Controls:
    right mouse drag    orbit the camera
    middle mouse drag   pan
    scroll wheel        zoom
    double-click a body
        or its label    follow it
    space               play / pause time
    right / left        step time forward / backward
    up / down           larger / smaller time step
    tab                 follow the next body
    m                   toggle real / logarithmic body sizes
    r                   reverse autoplay direction
    escape              reset camera to the Sun

Conventions:
    * Ephemeris states are heliocentric ecliptic km (x, y, z with z
      roughly out of the orbital plane). Ursina is y-up, so ecliptic
      (x, y, z) maps to scene (x, z, y) and the planets orbit in the
      ground plane.
    * Distances use POSITION_SCALE (1 unit = 10 million km).
    * Body sizes have two modes (see SizeMode): LOG (a readable
      logarithmic scale so everything is visible at once) and REAL
      (true radii — most bodies become sub-pixel, so a small fixed-size
      marker dot is drawn until you zoom in close enough for the real
      sphere to take over).
    * The Sun is unlit (it is the light source); a PointLight at the
      Sun lights the planets so they show day/night terminators.
"""

from __future__ import annotations
import os
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum, auto
from math import cos, log10, pi, sin, sqrt
from ursina import (AmbientLight,
                    Button,
                    Entity,
                    Mesh,
                    PointLight,
                    Text,
                    Ursina,
                    Vec3 as UrsinaVec3,
                    camera,
                    color as ursina_color,
                    load_texture,
                    mouse,
                    scene,
                    window)
from ursina.prefabs.editor_camera import EditorCamera
from jplephem.spk import SPK
from core.ephemeris import JplEphemeris
from core.flight_plan import FlightPlan
from core.lambert import MU_SUN, LambertNoConvergence, solve_lambert
from core.mission_planner import MissionPlanner, Objective
from core.missions import HistoricalMission, load_missions
from core.physics import G, circular_orbit_state, circular_orbit_velocity
from core.propagator import DEFAULT_DT_MAX, advance_coasting
from core.export import export_csv
from core.spaceship import PropulsionSystem, Spaceship
from core.trail import TrailPath
from core.vec3 import Vec3
from creators import load_bodies_from_json
from functions import convert_to_julian_date
from settings import EPHEMERIS_FILE, simulation_steps

# Surface textures (equirectangular maps from Solar System Scope, CC BY 4.0).
# Drop the 2k JPGs/PNG into TEXTURE_DIR (see textures/README.md); any that
# are missing fall back to the body's flat colour. There is no Solar System
# Scope map for Pluto, so it stays a coloured sphere.
TEXTURE_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
EXPORT_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
MISSIONS_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "missions.json")
# A historical-mission camera zoom wide enough to take in the outer planets.
HISTORICAL_CAMERA_Z: float = -200.0

# A custom (not-real) Earth -> Moon Hohmann trip, offered in the mission menu.
MOON_TRIP_NAME: str = "Earth-Moon trip"
MOON_PARKING_ALTITUDE_KM: float = 500.0
BODY_TEXTURES: dict[str, str] = {
    "Sun": "2k_sun.jpg",
    "Mercury": "2k_mercury.jpg",
    "Venus": "2k_venus_atmosphere.jpg",   # the visible cloud deck
    "Earth": "2k_earth_daymap.jpg",
    "Moon": "2k_moon.jpg",
    "Mars": "2k_mars.jpg",
    "Jupiter": "2k_jupiter.jpg",
    "Saturn": "2k_saturn.jpg",
    "Uranus": "2k_uranus.jpg",
    "Neptune": "2k_neptune.jpg",
}
SATURN_RING_TEXTURE: str = "2k_saturn_ring_alpha.png"

# Axial tilt (obliquity to the ecliptic), degrees. Values > 90 spin
# retrograde (Venus, Uranus, Pluto), which the tilt alone reproduces well
# enough with a uniform prograde spin about the tilted pole. Missing bodies
# default to 0.
AXIAL_TILT_DEG: dict[str, float] = {
    "Sun": 7.25,
    "Mercury": 0.03,
    "Venus": 177.4,
    "Earth": 23.44,
    "Moon": 6.68,
    "Mars": 25.19,
    "Jupiter": 3.13,
    "Saturn": 26.73,
    "Uranus": 97.77,
    "Neptune": 28.32,
    "Pluto": 122.53,
}


def load_texture_file(filename: str):
    """Load a texture from TEXTURE_DIR by filename, or None if it is absent."""
    if not os.path.exists(os.path.join(TEXTURE_DIR, filename)):
        return None
    return load_texture(os.path.splitext(filename)[0], folder=Path(TEXTURE_DIR))


def load_body_texture(name: str):
    """The loaded surface texture for a body, or None if there isn't one."""
    filename = BODY_TEXTURES.get(name)
    return load_texture_file(filename) if filename is not None else None


POSITION_SCALE: float = 1e-7        # ursina units per km (1 unit = 1e7 km)
ORBIT_SAMPLES: int = 180            # points per orbit line
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


def linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step: float = (stop - start) / (count - 1)
    return [start + step * i for i in range(count)]


class SizeMode(Enum):
    LOG = auto()    # logarithmic, everything visible at once
    REAL = auto()   # true radii, with markers for sub-pixel bodies


def hex_to_color(hex_color: str):
    """'#RRGGBB' -> ursina color."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return ursina_color.rgba(r, g, b, 1.0)


def ecliptic_to_scene(x_km: float, y_km: float, z_km: float) -> UrsinaVec3:
    """Heliocentric ecliptic km -> ursina scene units (y-up)."""
    return UrsinaVec3(x_km * POSITION_SCALE,
                      z_km * POSITION_SCALE,
                      y_km * POSITION_SCALE)


def vec3_to_scene(v: Vec3) -> UrsinaVec3:
    return ecliptic_to_scene(v.x, v.y, v.z)


def log_diameter(radius_km: float) -> float:
    """
    Logarithmic size (scene units) so everything is visible at once:
    Moon ~0.66, Earth ~0.92, Jupiter ~1.9, Sun ~2.8 diameter.
    """
    return max(0.15, 0.2 * log10(radius_km / 10.0)) * 2.0


def real_diameter(radius_km: float) -> float:
    """True diameter in scene units (often sub-pixel)."""
    return 2.0 * radius_km * POSITION_SCALE


def make_ring_mesh(inner: float, outer: float, segments: int = RING_SEGMENTS) -> Mesh:
    """
    A flat annulus in the local xz-plane (radii in local units), with UVs
    mapping the radial direction across u (0 at the inner edge, 1 at the
    outer) so a ring texture's radial bands land in the right place.
    """
    vertices: list[UrsinaVec3] = []
    uvs: list[tuple[float, float]] = []
    triangles: list[int] = []
    for i in range(segments + 1):
        angle = 2.0 * pi * i / segments
        c, s = cos(angle), sin(angle)
        vertices.append(UrsinaVec3(inner * c, 0.0, inner * s))
        vertices.append(UrsinaVec3(outer * c, 0.0, outer * s))
        uvs.append((0.0, 0.5))
        uvs.append((1.0, 0.5))
    for i in range(segments):
        b = 2 * i
        triangles += [b, b + 1, b + 3, b, b + 3, b + 2]
    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, mode="triangle")


class BodyEntity(Entity):
    """
    A celestial body. The `BodyEntity` itself is the position + axial-tilt
    frame; its child `globe` carries the textured sphere and spins about the
    (tilted) polar axis. Rings sit in the equatorial plane (children of the
    globe, so they share the tilt), and a fixed-apparent-size marker dot
    stands in when the real sphere is sub-pixel.
    """

    def __init__(self, name: str, body, is_star: bool) -> None:
        super().__init__()                       # bare position + tilt frame
        self.body = body
        self.body_name = name
        self.body_color = hex_to_color(body.color)
        self.rotation_z = AXIAL_TILT_DEG.get(name, 0.0)   # axial tilt (obliquity)

        # The visible, spinning sphere. With a surface texture the colour is
        # white (no tint) so the map shows true; otherwise fall back to the
        # body's flat colour. It carries the collider + body_name so clicking
        # the planet follows it.
        texture = load_body_texture(name)
        self.globe = Entity(parent=self,
                            model="sphere",
                            texture=texture,
                            color=ursina_color.white if texture else self.body_color,
                            scale=log_diameter(body.radius),
                            collider="sphere",
                            unlit=is_star)   # star is its own light; planets are lit
        self.globe.body_name = name
        if body.rings > 0:
            self._add_rings(body.rings)

        # A fixed-apparent-size dot shown only when the real sphere is
        # smaller than it (REAL mode, zoomed out).
        self.marker = Entity(model="sphere",
                             color=self.body_color,
                             collider="sphere",
                             unlit=True,
                             enabled=False)
        self.marker.body_name = name

    def _add_rings(self, ring_value: int) -> None:
        # Rings are children of the globe: their radii are in local units
        # (the sphere model has radius 0.5) so they scale with the planet,
        # and they share its axial tilt (the equatorial plane).
        if ring_value >= 3:        # Saturn: bright, broad
            inner, outer, ring_color = 0.7, 1.5, ursina_color.rgba(0.82, 0.72, 0.55, 0.7)
            # Use the real ring texture (with alpha for the gaps) when present.
            ring_texture = load_texture_file(SATURN_RING_TEXTURE)
            if ring_texture is not None:
                Entity(parent=self.globe,
                       model=make_ring_mesh(inner, outer),
                       texture=ring_texture,
                       color=ursina_color.white,
                       double_sided=True,
                       unlit=True)
                return
        else:                      # Jupiter / Uranus / Neptune: faint
            inner, outer, ring_color = 0.65, 1.05, ursina_color.rgba(0.8, 0.82, 0.85, 0.18)
        Entity(parent=self.globe,
               model=make_ring_mesh(inner, outer),
               color=ring_color,
               double_sided=True,
               unlit=True)

    def update_from_state(self, position_km: Vec3) -> None:
        self.position = vec3_to_scene(position_km)
        self.marker.position = self.position

    def update_spin(self, time_s: float) -> None:
        """Rotate the globe about its (tilted) polar axis for the given time."""
        period: float = self.body.rotation_period
        if period > 0:
            self.globe.rotation_y = (time_s / period * 360.0) % 360.0

    def apply_size(self, mode: SizeMode, camera_distance: float) -> None:
        """Resize the sphere/marker for the current mode and zoom level."""
        if mode is SizeMode.LOG:
            self.globe.scale = log_diameter(self.body.radius)
            self.marker.enabled = False
        else:
            diameter = real_diameter(self.body.radius)
            self.globe.scale = diameter
            marker_size = camera_distance * MARKER_APPARENT_SIZE
            self.marker.world_scale = marker_size
            self.marker.enabled = diameter < marker_size


class TrailEntity:
    """Renders a craft's growing trajectory as a decimated line."""

    def __init__(self, color, min_separation_km: float, max_points: int) -> None:
        self.path = TrailPath(min_separation_km=min_separation_km,
                              max_points=max_points)
        self.entity = Entity(model=Mesh(vertices=[], mode="line", thickness=2),
                             color=color,
                             unlit=True)

    def record(self, position_km: Vec3) -> None:
        if self.path.add(position_km) and len(self.path) >= 2:
            self.entity.model.vertices = [vec3_to_scene(p) for p in self.path.points]
            self.entity.model.generate()

    def clear(self) -> None:
        self.path.clear()
        self.entity.model.vertices = []
        self.entity.model.generate()


class SpaceshipEntity(Entity):
    """
    A craft rendered like a tiny body: a 1 km sphere (always sub-pixel at
    solar-system scale) shown via a fixed-apparent-size marker dot, exactly
    like the planet markers, plus its persistent trajectory trail.
    """

    def __init__(self, name: str, color=ursina_color.azure) -> None:
        super().__init__(model="sphere", color=color,
                         scale=real_diameter(SHIP_RADIUS_KM), unlit=True)
        self.craft_name = name
        # A small dot of fixed apparent size, so the craft stays visible
        # (and selectable) however far the camera is. Carries body_name so
        # double-click follow could pick it up like a body marker.
        self.marker = Entity(model="sphere", color=color,
                             collider="sphere", unlit=True)
        self.marker.body_name = name
        self.trail = TrailEntity(color=color,
                                 min_separation_km=2.0e6,
                                 max_points=4000)

    def apply_size(self, camera_distance: float) -> None:
        self.marker.world_scale = camera_distance * MARKER_APPARENT_SIZE

    def set_color(self, color) -> None:
        self.color = color
        self.marker.color = color
        self.trail.entity.color = color

    def sync(self, position_km: Vec3) -> None:
        self.position = vec3_to_scene(position_km)
        self.marker.position = self.position
        self.trail.record(position_km)


class SolaraApp(Entity):
    """Owns simulation time, body entities, HUD and input handling."""

    def __init__(self, ephemeris: JplEphemeris, bodies: dict, epoch: datetime) -> None:
        super().__init__()
        self.ephemeris = ephemeris
        self.bodies = bodies
        self.epoch = epoch
        self.sim_time_s: float = 0.0
        self.time_step_index: int = DEFAULT_TIME_STEP_INDEX
        self.auto_play: bool = False
        self.play_direction: float = 1.0
        self.size_mode: SizeMode = SizeMode.LOG
        self.follow_names: list[str] = list(bodies.keys())
        self.follow_index: int = 0

        self.body_entities: dict[str, BodyEntity] = {
            name: BodyEntity(name, body, is_star=(name == "Sun"))
            for name, body in bodies.items()
        }
        self._draw_orbit_lines()
        self._setup_lighting()

        self.planner = MissionPlanner(ephemeris=ephemeris, mu=MU_SUN)
        self.missions: dict[str, HistoricalMission] = load_missions(MISSIONS_FILE)
        self.mission_label: str = ""
        # Historical-mission replay state (a real craft coasting under full
        # N-body gravity). Distinct from the planned FLY_TO missions.
        self.historical_active: bool = False
        # Reactionless "test" drive for FLY_TO craft: thrust without spending
        # mass, so any mission is reachable and captures never run dry.
        self.use_test_ship: bool = False
        # Earth-Moon round-trip state (a scripted return burn near the Moon).
        self.moon_trip: bool = False
        self._moon_return_at: float = 0.0
        self._moon_returning: bool = False
        self._moon_r1: float = 0.0
        self._moon_mu: float = 0.0
        # The craft's home: while idle it rides a (kinematic) circular
        # parking orbit around this body, which is also where missions
        # depart from. The home body is excluded from FLY_TO destinations.
        self.home_body: str = DEFAULT_HOME_BODY
        # Active-mission state, used to drive mid-course corrections.
        self.mission_active: bool = False
        self.mission_target: str = ""
        self.mission_departure_time: float = 0.0
        self.mission_arrival_time: float = 0.0
        self.mission_capture_km: float = 0.0
        self.mission_insertion_budget: float = 6.0   # km/s, sized per mission
        self.mission_insertion_altitude: float = INSERTION_ALTITUDE_KM
        self._mcc_index: int = 0
        # Patched-conic gravity for the active mission: Sun + target only.
        # The cruise is Sun-dominated and must NOT feel the origin planet's
        # well (the craft launches from that planet's position), while the
        # target's gravity is what captures it for insertion.
        self.mission_gravity_bodies: dict = {}

        # The craft entity always exists. `sim_ship` holds the simulated
        # mission craft when a mission is active; while idle (`parked`) the
        # entity is placed kinematically on a parking orbit around home.
        self.ships: dict[str, SpaceshipEntity] = {SHIP_NAME: SpaceshipEntity(SHIP_NAME)}
        self.sim_ship: Spaceship | None = None
        self.parked: bool = True
        self._sync_bodies_to_time(self.sim_time_s)

        self.camera_rig = EditorCamera(rotation_smoothing=2,
                                       pan_speed=(2, 2),
                                       zoom_speed=2)
        # `camera.lens` is absent in headless mode; clip planes only
        # matter with a real render window anyway.
        if hasattr(camera, "lens"):
            camera.clip_plane_near = CAMERA_NEAR_CLIP
            camera.clip_plane_far = CAMERA_FAR_CLIP
        self._reset_camera()

        # Name labels: 2D UI Text whose screen position is updated each
        # frame from each target's projected world position. (Parenting
        # Text to world entities does not render reliably in Ursina.)
        self.date_text = Text(text="", position=(-0.85, 0.47), scale=0.9)
        self.status_text = Text(text="", position=(-0.85, 0.43), scale=0.8,
                                color=ursina_color.yellow)
        self.follow_text = Text(text="", position=(-0.85, 0.39), scale=0.8,
                                color=ursina_color.green)
        self.mission_text = Text(text="", position=(-0.85, 0.35), scale=0.8,
                                 color=ursina_color.azure)
        self.note_text = Text(text="", position=(-0.85, 0.31), scale=0.75,
                              color=ursina_color.white)
        self.help_text = Text(
            text="space play | arrows step/timestep | dbl-click/tab follow | m sizes | "
                 "r reverse | h start at | f fly to | v mission | t test drive | e export | esc reset",
            position=(-0.85, -0.47), scale=0.7, color=ursina_color.white66)

        self._label_targets: list[tuple[Text, Entity, str]] = []
        for name, entity in self.body_entities.items():
            self._label_targets.append(
                (Text(text=name, scale=0.7, origin=(0, 0),
                      color=ursina_color.white), entity, name))
        for name, ship in self.ships.items():
            self._label_targets.append(
                (Text(text=name, scale=0.7, origin=(0, 0),
                      color=ursina_color.azure), ship, name))
        # Per-frame screen rectangles of placed labels: (name, x, y, w, h).
        self._label_hitboxes: list[tuple[str, float, float, float, float]] = []

        self._build_menus()

        self.refresh_positions()
        self.refresh_hud()

    # ------------------------------------------------------------------
    # Simulation time
    # ------------------------------------------------------------------

    @property
    def time_step_s(self) -> float:
        return float(simulation_steps[self.time_step_index][1])

    @property
    def time_step_name(self) -> str:
        return simulation_steps[self.time_step_index][0]

    @property
    def current_date(self) -> datetime:
        return self.epoch + timedelta(seconds=self.sim_time_s)

    def advance(self, dt_s: float) -> None:
        if self.mission_active and not self.parked and dt_s > 0.0 and self.sim_ship is not None:
            # Step the mission forward in body-sync chunks: the ship
            # sub-steps internally, but the target body must be re-synced
            # at the same cadence or the approach/capture chases a stale
            # planet position (a day's worth of its motion is millions of
            # km — enough to wreck the capture).
            self._advance_mission(dt_s)
        elif self.historical_active and dt_s > 0.0 and self.sim_ship is not None:
            self._advance_historical(dt_s)
        else:
            self.sim_time_s += dt_s
            self._sync_bodies_to_time(self.sim_time_s)
            self._advance_ship(dt_s)
        if (self.moon_trip and self._moon_returning
                and self.sim_time_s >= self._moon_return_at):
            self._moon_return_burn()
            self._moon_returning = False
        self.refresh_positions()
        self.refresh_hud()

    def _advance_historical(self, dt_s: float) -> None:
        """Coast a real craft forward under full N-body gravity (adaptive)."""
        advance_coasting(self.sim_ship, self.ephemeris, self.bodies,
                         self.sim_time_s, dt_s)
        self.sim_time_s += dt_s
        self._sync_bodies_to_time(self.sim_time_s)

    def _advance_mission(self, dt_s: float) -> None:
        fine_chunk: float = self.sim_ship.max_integration_dt
        remaining: float = dt_s
        while remaining > 1e-6:
            target = self.bodies[self.mission_target]
            distance: float = (self.sim_ship.position - target.position).magnitude()
            # Re-sync the target on a cadence that tightens as the craft
            # closes in (its position must be fresh during the approach and
            # capture, but daily is plenty out in the cruise). A gradual
            # far -> approach -> near refinement avoids a coarse step
            # overshooting the sensitive approach with a stale planet.
            cap: float = self.mission_capture_km
            if distance <= 4.0 * cap:
                chunk = fine_chunk          # capture: every sub-step
            elif distance <= 20.0 * cap:
                chunk = 3600.0              # approach: hourly
            else:
                chunk = 86400.0             # cruise: daily
            step: float = min(chunk, remaining)
            self.sim_time_s += step
            for name, body in self.mission_gravity_bodies.items():
                position, velocity = self.ephemeris.state(name, self.sim_time_s)
                body.position = position
                body.velocity = velocity
            self.sim_ship.step_forward(step, self.mission_gravity_bodies)
            self._maybe_correct_course()
            remaining -= step
        # Re-sync everything for rendering at the final time.
        self._sync_bodies_to_time(self.sim_time_s)

    # ------------------------------------------------------------------
    # Simulated ship
    # ------------------------------------------------------------------

    def _parking_position(self) -> Vec3:
        """
        Kinematic circular parking orbit around the home body (ecliptic
        plane). Computed directly from the body's live position so it
        tracks the planet exactly at any time step — far more robust than
        integrating a tight orbit around a fast-moving body with coarse
        display steps. Real physics kicks in once a mission launches.
        """
        body = self.bodies[self.home_body]
        orbit_radius: float = body.radius + PARKING_ALTITUDE_KM
        angular_rate: float = circular_orbit_velocity(body.mass, orbit_radius) / orbit_radius
        angle: float = angular_rate * self.sim_time_s
        offset = Vec3(orbit_radius * cos(angle), orbit_radius * sin(angle), 0.0)
        return body.position + offset

    def _sync_bodies_to_time(self, time_s: float) -> None:
        """Move the body objects to their ephemeris state, for live gravity."""
        for name, body in self.bodies.items():
            position, velocity = self.ephemeris.state(name, time_s)
            body.position = position
            body.velocity = velocity

    def _advance_ship(self, dt_s: float) -> None:
        """
        While parked the craft is kinematic (placed in refresh_positions),
        so there is nothing to integrate. During a mission the simulated
        craft flies patched-conic (Sun + target): forward steps simulate
        and sub-step, backward steps replay history.
        """
        if self.parked or self.sim_ship is None or dt_s == 0.0:
            return
        if dt_s > 0.0:
            self.sim_ship.step_forward(dt_s, self.mission_gravity_bodies)
        else:
            self.sim_ship.step_backwards()

    # ------------------------------------------------------------------
    # FLY_TO: plan and launch a transfer
    # ------------------------------------------------------------------

    def _build_menus(self) -> None:
        """Hidden vertical button menus: set-home ('h'), fly-to ('f'), mission ('v')."""
        self.fly_menu_open: bool = False
        self.home_menu_open: bool = False
        self.mission_menu_open: bool = False
        self.fly_title, self.fly_buttons = self._build_button_menu(
            "Fly to:", x=0.72, color=ursina_color.azure, on_pick=self._fly_to)
        self.home_title, self.home_buttons = self._build_button_menu(
            "Start at:", x=0.72, color=ursina_color.lime, on_pick=self._set_home)
        self.mission_menu_title, self.mission_buttons = self._build_button_menu(
            "Mission:", x=0.72, color=ursina_color.orange, on_pick=self._load_mission,
            names=list(self.missions.keys()) + [MOON_TRIP_NAME])

    def _build_button_menu(self, title: str, x: float, color, on_pick,
                           names: list[str] | None = None) -> tuple[Text, dict[str, Button]]:
        if names is None:
            names = [name for name, body in self.bodies.items()
                     if body.parent_body == "Sun"]
        title_text = Text(text=title, position=(x - 0.10, 0.45), scale=0.9,
                          color=color, enabled=False)
        buttons: dict[str, Button] = {}
        for i, name in enumerate(names):
            button = Button(text=name, scale=(0.2, 0.05),
                            position=(x, 0.38 - i * 0.06),
                            color=color.tint(-0.4), enabled=False)
            button.on_click = (lambda target=name: on_pick(target))
            buttons[name] = button
        return title_text, buttons

    def _toggle_fly_menu(self) -> None:
        was_open = self.fly_menu_open
        self._close_menus()
        if not was_open:
            self._set_fly_menu(True)

    def _toggle_home_menu(self) -> None:
        was_open = self.home_menu_open
        self._close_menus()
        if not was_open:
            self._set_home_menu(True)

    def _toggle_mission_menu(self) -> None:
        was_open = self.mission_menu_open
        self._close_menus()
        if not was_open:
            self._set_mission_menu(True)

    def _close_menus(self) -> None:
        self._set_fly_menu(False)
        self._set_home_menu(False)
        self._set_mission_menu(False)

    def _set_fly_menu(self, open_: bool) -> None:
        self.fly_menu_open = open_
        self.fly_title.enabled = open_
        for name, button in self.fly_buttons.items():
            button.enabled = open_ and name != self.home_body   # can't fly to where you are

    def _set_home_menu(self, open_: bool) -> None:
        self.home_menu_open = open_
        self.home_title.enabled = open_
        for button in self.home_buttons.values():
            button.enabled = open_

    def _set_mission_menu(self, open_: bool) -> None:
        self.mission_menu_open = open_
        self.mission_menu_title.enabled = open_
        for button in self.mission_buttons.values():
            button.enabled = open_

    def _set_home(self, body: str) -> None:
        """Park the craft around `body`, ending any active mission."""
        self._close_menus()
        self.home_body = body
        self.parked = True
        self.sim_ship = None
        self.mission_active = False
        self.historical_active = False
        self.moon_trip = False
        self.mission_label = ""
        self.ships[SHIP_NAME].set_color(ursina_color.azure)
        self.ships[SHIP_NAME].trail.clear()
        self.follow(body)
        self.refresh_positions()
        self.refresh_hud()

    def _make_historical_ship(self, mission: HistoricalMission) -> Spaceship:
        """A coasting craft at a real spacecraft's recorded launch-era state."""
        return Spaceship(structure_mass=mission.structure_mass,
                         payload_mass=0.0,
                         main_propulsion=PropulsionSystem(),     # inert: it coasts
                         initial_position=mission.position,
                         initial_velocity=mission.velocity,
                         flight_plan=FlightPlan(),
                         max_integration_dt=DEFAULT_DT_MAX)

    def _load_mission(self, name: str) -> None:
        """Load a mission from the menu (a real spacecraft, or the Moon trip)."""
        if name == MOON_TRIP_NAME:
            self._load_moon_mission()
            return
        self._close_menus()
        mission = self.missions[name]
        # The craft's epoch is JD(TDB); place the clock there relative to the
        # app's ephemeris epoch so craft and planets share the same instant.
        self.sim_time_s = (mission.epoch_jd - self.ephemeris.epoch_jd) * 86400.0
        self._sync_bodies_to_time(self.sim_time_s)

        self.sim_ship = self._make_historical_ship(mission)
        self.parked = False
        self.mission_active = False
        self.historical_active = True
        self.moon_trip = False
        self.mission_target = name
        self.mission_departure_time = self.sim_time_s

        entity = self.ships[SHIP_NAME]
        entity.set_color(hex_to_color(mission.color))
        entity.trail.clear()
        entity.sync(self.sim_ship.position)

        if mission.follow in self.follow_names:
            self.follow(mission.follow)
        camera.z = HISTORICAL_CAMERA_Z
        self.camera_rig.target_z = HISTORICAL_CAMERA_Z

        self.auto_play = False
        entity.trail.path.min_separation_km = 2.0e6   # interplanetary trail spacing
        self.mission_label = f"{name}: {mission.description}"
        self._notify(f"{name} loaded at {self.current_date:%Y-%m-%d}. Press space to fly.")
        self.refresh_positions()
        self.refresh_hud()

    def _load_moon_mission(self) -> None:
        """
        A made-up Earth->Moon->Earth trip (not a real mission): one prograde burn
        from a low parking orbit raises apogee to the Moon's distance — a Hohmann
        transfer. The closed ellipse coasts out to the Moon and falls back to
        Earth on its own; departure is phased so apogee meets the Moon, giving a
        lunar flyby on the way. Flown under full N-body gravity with the
        reactionless test drive, so the burn is free.
        """
        self._close_menus()
        self.sim_time_s = 0.0                      # the app's epoch ("now")
        self._sync_bodies_to_time(self.sim_time_s)
        earth = self.bodies["Earth"]
        moon = self.bodies["Moon"]
        # G is SI (m^3/kg/s^2); positions are km, so mu must be km^3/s^2.
        mu_earth: float = G * earth.mass / 1.0e9

        r1: float = earth.radius + MOON_PARKING_ALTITUDE_KM
        # Iterate the transfer time and the Moon's arrival state together: the
        # apogee must match where the Moon will be after the transfer, and the
        # transfer time depends on that distance.
        moon_future = moon.position - earth.position
        moon_velocity = moon.velocity - earth.velocity
        for _ in range(3):
            r2: float = moon_future.magnitude()
            semi_major: float = 0.5 * (r1 + r2)
            tof: float = pi * sqrt(semi_major ** 3 / mu_earth)
            arrival_earth = self.ephemeris.state("Earth", self.sim_time_s + tof)
            arrival_moon = self.ephemeris.state("Moon", self.sim_time_s + tof)
            moon_future = arrival_moon[0] - arrival_earth[0]
            moon_velocity = arrival_moon[1] - arrival_earth[1]

        # Inject directly onto the Hohmann transfer. A 180-degree transfer puts
        # apogee opposite the perigee, so place the perigee on the far side from
        # the Moon's arrival point (in 3D, accounting for the Moon's ~5deg
        # inclination), with the perigee velocity aimed along the Moon's motion.
        # A LEO->Moon transfer is ~99% of escape speed, so apogee is
        # hypersensitive to that velocity — injecting the exact value is far
        # more reliable than delivering the kick over a finite burn.
        apogee_dir = moon_future.normalized()
        perigee_dir = apogee_dir * -1.0
        # Perigee velocity: perpendicular to the radius, along the Moon's motion.
        prograde = (moon_velocity - perigee_dir * moon_velocity.dot(perigee_dir)).normalized()
        v_transfer: float = sqrt(mu_earth * (2.0 / r1 - 1.0 / semi_major))
        position = earth.position + perigee_dir * r1
        velocity = earth.velocity + prograde * v_transfer
        plan = FlightPlan().add_coast(duration=2.2 * tof)           # out and back

        self.sim_ship = Spaceship(
            structure_mass=5000.0, payload_mass=0.0,
            main_propulsion=PropulsionSystem(max_thrust=3.0e6, reactionless=True),
            initial_position=position, initial_velocity=velocity,
            flight_plan=plan, max_integration_dt=DEFAULT_DT_MAX)
        self.parked = False
        self.mission_active = False
        self.historical_active = True              # full N-body flight (with a plan)
        self.mission_target = MOON_TRIP_NAME
        self.mission_departure_time = self.sim_time_s
        # Schedule a return burn at arrival (~apogee, near the Moon): the lunar
        # flyby would otherwise fling the craft off course, so drop it onto a
        # return ellipse back to Earth (a free burn for the reactionless drive).
        self.moon_trip = True
        self._moon_returning = True
        self._moon_return_at = self.sim_time_s + tof
        self._moon_r1 = r1
        self._moon_mu = mu_earth

        entity = self.ships[SHIP_NAME]
        entity.set_color(hex_to_color("#d8d8d8"))
        entity.trail.path.min_separation_km = 5000.0   # fine trail for the Earth-Moon scale
        entity.trail.clear()
        entity.sync(self.sim_ship.position)

        self.size_mode = SizeMode.REAL             # Earth & Moon as dots at this scale
        self.follow("Earth")
        camera.z = -0.2
        self.camera_rig.target_z = -0.2

        self.auto_play = False
        self.mission_label = f"{MOON_TRIP_NAME}: Hohmann to the Moon and back (~{tof/86400.0:.1f} d each way)"
        self._notify(f"{MOON_TRIP_NAME} ready. Press space to fly to the Moon and back.")
        self.refresh_positions()
        self.refresh_hud()

    def _moon_return_burn(self) -> None:
        """At the Moon, drop the craft onto a return ellipse back to Earth."""
        earth = self.bodies["Earth"]
        relative_position = self.sim_ship.position - earth.position
        radius = relative_position.magnitude()
        radial_hat = relative_position.normalized()
        relative_velocity = self.sim_ship.velocity - earth.velocity
        tangential = relative_velocity - radial_hat * relative_velocity.dot(radial_hat)
        # Apogee speed of an ellipse with apogee = here, perigee = parking orbit.
        semi_major = 0.5 * (self._moon_r1 + radius)
        return_speed = sqrt(self._moon_mu * (2.0 / radius - 1.0 / semi_major))
        # Reactionless cheat: set the velocity directly to the return state.
        self.sim_ship._velocity = earth.velocity + tangential.normalized() * return_speed
        self._notify(f"{MOON_TRIP_NAME}: at the Moon — return burn, heading back to Earth.")

    def _notify(self, message: str) -> None:
        self.note_text.text = message

    def _export_trajectory(self) -> None:
        """Write the current craft's recorded flight to exports/<...>.csv."""
        if self.sim_ship is None or len(self.sim_ship.history) < 2:
            self._notify("Nothing to export — fly a mission first.")
            return
        os.makedirs(EXPORT_DIR, exist_ok=True)
        if self.historical_active:
            basename = self.mission_target            # the mission's name
        else:
            basename = f"{self.home_body}_to_{self.mission_target or 'free'}"
        stamp = f"{self.current_date:%Y%m%dT%H%M%S}"
        filename = f"{basename}_{stamp}.csv".replace(" ", "_")
        path = os.path.join(EXPORT_DIR, filename)
        # start_time_s = mission start, so the exported time_s is absolute
        # simulation time (epoch + time_s reconstructs the calendar date).
        rows = export_csv(self.sim_ship, path, start_time_s=self.mission_departure_time)
        self._notify(f"Exported {rows} states -> exports/{filename}")

    def _transfer_grid(self, origin: str, target: str) -> tuple[list[float], list[float]]:
        """
        A porkchop search grid: departures over (up to) one synodic period
        starting now, and flight times bracketing the Hohmann time between
        the two bodies' current radii.
        """
        now: float = self.sim_time_s
        r1: float = self.ephemeris.state(origin, now)[0].magnitude()
        r2: float = self.ephemeris.state(target, now)[0].magnitude()
        semi_major: float = 0.5 * (r1 + r2)
        hohmann_tof: float = pi * sqrt(semi_major**3 / MU_SUN)
        flight_times: list[float] = linspace(0.6 * hohmann_tof, 1.6 * hohmann_tof,
                                             GRID_FLIGHT_SAMPLES)

        period_origin: float = self.bodies[origin].orbital_period * 86400.0
        period_target: float = self.bodies[target].orbital_period * 86400.0
        rate_difference: float = abs(1.0 / period_origin - 1.0 / period_target)
        synodic: float = (1.0 / rate_difference) if rate_difference > 0 else period_target
        window: float = min(synodic, MAX_DEPARTURE_WINDOW_S)
        departure_times: list[float] = linspace(now, now + window, GRID_DEPARTURE_SAMPLES)
        return departure_times, flight_times

    def _capture_radius(self, target: str) -> float:
        """
        Capture shell at a fraction of the sphere of influence: it only has
        to be wide enough to reliably latch the approach. The insertion then
        coasts down to periapsis and circularizes there, so the *resulting*
        orbit is low and well inside the SOI (stable against the Sun's
        tide), regardless of how wide this shell is.
        """
        body = self.bodies[target]
        sun = self.bodies["Sun"]
        target_radius: float = self.ephemeris.state(target, self.sim_time_s)[0].magnitude()
        sphere_of_influence: float = target_radius * (body.mass / sun.mass) ** 0.4
        return 0.5 * sphere_of_influence

    def _make_mission_ship(self, position: Vec3, velocity: Vec3,
                           plan) -> Spaceship:
        """A craft with ample thrust and fuel to fly the transfer and insert."""
        if self.use_test_ship:
            # Reactionless cheat drive: unlimited delta-v, constant mass.
            engine = PropulsionSystem(max_thrust=3.0e6, reactionless=True)
        else:
            engine = PropulsionSystem(max_thrust=3.0e6,
                                      specific_impulse=450.0,
                                      exhaust_velocity=4500.0,
                                      fuel_mass=1.2e5)
        return Spaceship(structure_mass=4000.0,
                         payload_mass=1000.0,
                         main_propulsion=engine,
                         initial_position=position,
                         initial_velocity=velocity,
                         flight_plan=plan,
                         max_integration_dt=MISSION_SHIP_MAX_DT)

    def _fly_to(self, target: str) -> None:
        """Plan the cheapest transfer to `target` and launch the mission."""
        self._set_fly_menu(False)
        if target == self.home_body:
            return
        origin = self.home_body
        try:
            departures, flights = self._transfer_grid(origin, target)
            solution = self.planner.plan_transfer(
                origin=origin, target=target,
                departure_times=departures, flight_times=flights,
                objective=Objective.MIN_DELTA_V)
        except LambertNoConvergence:
            self.mission_label = f"no {origin}->{target} window found"
            self.refresh_hud()
            return

        capture_km = self._capture_radius(target)
        # Circularize well above the surface (a fraction of the SOI) rather
        # than at the centre-aimed periapsis: the transfer aims at the
        # planet centre, so the natural periapsis grazes the surface, where
        # a fast deep burn can't be integrated cleanly. Braking higher up
        # gives a high but *bound and stable* orbit (well inside the SOI).
        # A true low orbit needs B-plane targeting (future work).
        insertion_altitude = max(INSERTION_ALTITUDE_KM,
                                 0.15 * capture_km - self.bodies[target].radius)
        # Retrograde capture: budget enough to brake the arrival excess into
        # a bound orbit, with margin for the gravitational speed-up on the
        # way down to the circularization altitude.
        insertion_budget = 3.0 * solution.arrival_delta_v.magnitude() + 2.0
        plan = self.planner.to_flight_plan(
            solution, burn_duration=600.0, orbit_insertion=True,
            insertion_altitude_km=insertion_altitude,
            capture_radius_km=capture_km,
            insertion_max_delta_v_km_s=insertion_budget)
        self._launch_mission(solution, plan, capture_km, insertion_budget, insertion_altitude)

    def _launch_mission(self, solution, plan, capture_km: float,
                        insertion_budget: float, insertion_altitude: float) -> None:
        """Warp the clock to the launch window and place the craft at origin."""
        self.sim_time_s = solution.departure_time
        self._sync_bodies_to_time(self.sim_time_s)
        position, velocity = self.ephemeris.state(solution.origin, solution.departure_time)
        self.sim_ship = self._make_mission_ship(position, velocity, plan)
        self.parked = False

        entity = self.ships[SHIP_NAME]
        entity.set_color(ursina_color.azure)
        entity.trail.path.min_separation_km = 2.0e6   # interplanetary trail spacing
        entity.trail.clear()
        entity.sync(self.sim_ship.position)

        self.mission_active = True
        self.historical_active = False
        self.moon_trip = False
        self.mission_target = solution.target
        self.mission_departure_time = solution.departure_time
        self.mission_arrival_time = solution.arrival_time
        self.mission_capture_km = capture_km
        self.mission_insertion_budget = insertion_budget
        self.mission_insertion_altitude = insertion_altitude
        self.mission_gravity_bodies = {"Sun": self.bodies["Sun"],
                                       solution.target: self.bodies[solution.target]}
        self._mcc_index = 0

        self.auto_play = False
        self.mission_label = (f"{solution.origin} -> {solution.target}  "
                              f"dv {solution.total_delta_v:.2f} km/s  "
                              f"tof {solution.time_of_flight / 86400.0:.0f} d  "
                              f"(press space)")
        self.refresh_positions()
        self.refresh_hud()

    def _maybe_correct_course(self) -> None:
        """
        Re-solve Lambert from the live state and burn the correction when
        the transfer passes a scheduled mid-course-correction fraction.
        This is what keeps the craft on course to a *moving* target despite
        the coarse plan, the (smeared) finite burns and N-body drift.
        """
        if (not self.mission_active or self.sim_ship is None
                or self._mcc_index >= len(MCC_FRACTIONS)):
            return
        total: float = self.mission_arrival_time - self.mission_departure_time
        remaining: float = self.mission_arrival_time - self.sim_time_s
        if total <= 0.0:
            return
        progress: float = 1.0 - remaining / total
        if progress < MCC_FRACTIONS[self._mcc_index]:
            return
        self._mcc_index += 1

        if remaining < MIN_MCC_LEAD_S:
            return
        target_position = self.ephemeris.state(self.mission_target,
                                               self.mission_arrival_time)[0]
        # Inside the capture shell the insertion controller takes over.
        if (self.sim_ship.position - self.bodies[self.mission_target].position
                ).magnitude() < self.mission_capture_km:
            return
        try:
            lambert = solve_lambert(r1=self.sim_ship.position,
                                    r2=target_position,
                                    time_of_flight=remaining,
                                    mu=MU_SUN)
        except LambertNoConvergence:
            return
        correction: Vec3 = lambert.v1 - self.sim_ship.velocity
        if correction.magnitude() < 1.0e-4:   # km/s, negligible
            return
        self.sim_ship.flight_plan = (
            FlightPlan()
            .add_delta_v_vector(delta_v_vector_km_s=correction, duration=600.0)
            .add_orbit_insertion(body=self.mission_target,
                                 target_altitude_km=self.mission_insertion_altitude,
                                 capture_radius_km=self.mission_capture_km,
                                 max_delta_v_km_s=self.mission_insertion_budget))

    # ------------------------------------------------------------------
    # Camera / following
    # ------------------------------------------------------------------

    def _reset_camera(self) -> None:
        self.follow_index = 0   # the Sun is first in the dict
        self.camera_rig.rotation_x = DEFAULT_CAMERA_PITCH
        self.camera_rig.rotation_y = 0.0
        camera.z = DEFAULT_CAMERA_Z
        self.camera_rig.target_z = DEFAULT_CAMERA_Z
        self.camera_rig.position = self.body_entities[
            self.follow_names[self.follow_index]].position

    def follow(self, name: str) -> None:
        if name in self.follow_names:
            self.follow_index = self.follow_names.index(name)
            self.refresh_positions()
            self.refresh_hud()

    # ------------------------------------------------------------------
    # Scene setup
    # ------------------------------------------------------------------

    def _setup_lighting(self) -> None:
        """A point light at the Sun (origin) plus faint ambient fill."""
        self.sun_light = PointLight(parent=scene, position=(0, 0, 0),
                                    color=ursina_color.white)
        self.ambient = AmbientLight(color=ursina_color.rgba(0.18, 0.18, 0.22, 1.0))

    def _draw_orbit_lines(self) -> None:
        """One faint line per body that orbits the Sun directly."""
        for name, body in self.bodies.items():
            if body.parent_body != "Sun" or body.orbital_period <= 0:
                continue
            period_s: float = body.orbital_period * 86400.0
            points: list[UrsinaVec3] = []
            for i in range(ORBIT_SAMPLES + 1):
                t: float = self.sim_time_s + period_s * i / ORBIT_SAMPLES
                position, _ = self.ephemeris.state(name, t)
                points.append(vec3_to_scene(position))
            Entity(model=Mesh(vertices=points, mode="line", thickness=1),
                   color=ursina_color.rgba(1, 1, 1, 0.15),
                   unlit=True)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def refresh_positions(self) -> None:
        for name, entity in self.body_entities.items():
            position, _ = self.ephemeris.state(name, self.sim_time_s)
            entity.update_from_state(position)
            entity.update_spin(self.sim_time_s)
        # Parked: kinematic parking orbit. Mission: the simulated craft.
        ship_position = (self._parking_position() if self.parked
                         else self.sim_ship.position)
        self.ships[SHIP_NAME].sync(ship_position)
        followed = self.body_entities[self.follow_names[self.follow_index]]
        self.camera_rig.position = followed.position

    def refresh_hud(self) -> None:
        self.date_text.text = f"{self.current_date:%Y-%m-%d %H:%M:%S}"
        play_state: str = ("RUNNING" if self.play_direction > 0 else "REVERSED") \
            if self.auto_play else "PAUSED"
        self.status_text.text = (f"Step: {self.time_step_name}  [{play_state}]"
                                 f"   Sizes: {self.size_mode.name}"
                                 + ("   [TEST DRIVE]" if self.use_test_ship else ""))
        self.follow_text.text = f"Following: {self.follow_names[self.follow_index]}"
        self.mission_text.text = f"Mission: {self.mission_label}" if self.mission_label else ""

    def apply_visual_sizes(self) -> None:
        """Per-frame: bodies' apparent sizes depend on camera distance."""
        cam = camera.world_position
        for entity in self.body_entities.values():
            distance = (entity.world_position - cam).length()
            entity.apply_size(self.size_mode, distance)
        for ship in self.ships.values():
            ship.apply_size((ship.world_position - cam).length())

    def update_labels(self) -> None:
        """
        Per-frame: place 2D labels over their projected world points,
        nudging vertically to avoid overlaps (closest body wins its
        preferred spot). Crude but good enough.
        """
        # `camera.lens` (needed by screen_position) only exists once a
        # render window is up; skip in headless mode.
        if not hasattr(camera, "lens"):
            return
        cam_pos = camera.world_position
        cam_fwd = camera.forward
        half_width = camera.aspect_ratio / 2.0

        # Gather visible candidates with their camera distance.
        candidates: list[tuple[float, Text, str, float, float]] = []
        for text, entity, name in self._label_targets:
            to_entity = entity.world_position - cam_pos
            in_front = (to_entity.x * cam_fwd.x
                        + to_entity.y * cam_fwd.y
                        + to_entity.z * cam_fwd.z) > 0
            screen = entity.screen_position
            if not in_front or abs(screen.x) > half_width or abs(screen.y) > 0.5:
                text.enabled = False
                continue
            candidates.append((to_entity.length(), text, name,
                               screen.x, screen.y + LABEL_VERTICAL_OFFSET))

        # Nearer bodies get first pick of their preferred position.
        candidates.sort(key=lambda c: c[0])
        self._label_hitboxes = []
        for _, text, name, x, y0 in candidates:
            w = max(text.width, 0.05)
            h = max(text.height, 0.03)
            placed = False
            for attempt in range(LABEL_NUDGE_ATTEMPTS + 1):
                for direction in ((1, -1) if attempt else (0,)):
                    y = y0 + direction * attempt * LABEL_NUDGE_STEP
                    if not self._overlaps_placed(x, y, w, h):
                        text.position = (x, y)
                        text.enabled = True
                        self._label_hitboxes.append((name, x, y, w, h))
                        placed = True
                        break
                if placed:
                    break
            text.enabled = placed

    def _overlaps_placed(self, x: float, y: float, w: float, h: float) -> bool:
        for _, px, py, pw, ph in self._label_hitboxes:
            if abs(x - px) * 2 < (w + pw) and abs(y - py) * 2 < (h + ph):
                return True
        return False

    # ------------------------------------------------------------------
    # Per-frame update and input (called by ursina)
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.auto_play:
            self.advance(self.time_step_s * self.play_direction)
        self.apply_visual_sizes()
        self.update_labels()

    def _follow_at_pointer(self) -> None:
        """Double-click: follow the hovered body, or a clicked label."""
        hovered = mouse.hovered_entity
        if hovered is not None and hasattr(hovered, "body_name"):
            self.follow(hovered.body_name)
            return
        mx, my = mouse.position.x, mouse.position.y
        for name, x, y, w, h in self._label_hitboxes:
            if abs(mx - x) * 2 <= w and abs(my - y) * 2 <= h:
                self.follow(name)
                return

    def input(self, key: str) -> None:
        if key == "double click":
            self._follow_at_pointer()
        elif key == "escape":
            self._reset_camera()
            self.refresh_hud()
        elif key == "space":
            self.auto_play = not self.auto_play
            self.refresh_hud()
        elif key == "r":
            self.play_direction *= -1.0
            self.refresh_hud()
        elif key == "m":
            self.size_mode = (SizeMode.REAL if self.size_mode is SizeMode.LOG
                              else SizeMode.LOG)
            self.refresh_hud()
        elif key == "f":
            self._toggle_fly_menu()
        elif key == "h":
            self._toggle_home_menu()
        elif key == "v":
            self._toggle_mission_menu()
        elif key == "t":
            self.use_test_ship = not self.use_test_ship
            self._notify(f"Test drive (reactionless) "
                         f"{'ON' if self.use_test_ship else 'OFF'} — applies to the next FLY_TO.")
            self.refresh_hud()
        elif key == "e":
            self._export_trajectory()
        elif key in ("right arrow", "right arrow hold"):
            self.advance(self.time_step_s)
        elif key in ("left arrow", "left arrow hold"):
            self.advance(-self.time_step_s)
        elif key == "up arrow":
            self.time_step_index = min(self.time_step_index + 1,
                                       len(simulation_steps) - 1)
            self.refresh_hud()
        elif key == "down arrow":
            self.time_step_index = max(self.time_step_index - 1, 0)
            self.refresh_hud()
        elif key == "tab":
            self.follow_index = (self.follow_index + 1) % len(self.follow_names)
            self.refresh_positions()
            self.refresh_hud()


def main() -> None:
    app = Ursina(title="Solara", borderless=False)
    window.color = ursina_color.black

    epoch = datetime.now()
    kernel = SPK.open(EPHEMERIS_FILE)
    bodies = load_bodies_from_json()
    ephemeris = JplEphemeris.from_bodies(kernel=kernel,
                                         bodies=bodies,
                                         epoch_jd=convert_to_julian_date(epoch))
    SolaraApp(ephemeris=ephemeris, bodies=bodies, epoch=epoch)
    try:
        app.run()
    finally:
        kernel.close()


if __name__ == "__main__":
    main()
