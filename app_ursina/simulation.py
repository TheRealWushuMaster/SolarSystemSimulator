"""
Solara — Ursina renderer.

New graphics front-end on top of the `core` package. The old Tkinter
app (legacy/GUI.py) is untouched and still runnable; this is its replacement.

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
from datetime import datetime, timedelta
from math import cos, sin
from ursina import (AmbientLight,
                    Entity,
                    Mesh,
                    PointLight,
                    Text,
                    Ursina, Vec2,
                    camera,
                    color as ursina_color,
                    scene,
                    window)
from ursina.prefabs.editor_camera import EditorCamera
from jplephem.spk import SPK
from config import EPHEMERIS_FILE, ORBIT_SAMPLES, simulation_steps
from core.bodies import CelestialBody, load_bodies_from_json
from core.ephemeris import JplEphemeris
from core.lambert import MU_SUN
from core.mission_planner import MissionPlanner
from core.missions import HistoricalMission, load_missions
from core.physics import circular_orbit_velocity
from core.propagator import advance_coasting
from core.spaceship import Spaceship
from core.time import convert_to_julian_date
from core.vec3 import Vec3
from app_ursina.config import (DEFAULT_CAMERA_PITCH, DEFAULT_CAMERA_Z,
                               DEFAULT_HOME_BODY, DEFAULT_TIME_STEP_INDEX,
                               CAMERA_FAR_CLIP, CAMERA_NEAR_CLIP,
                               INSERTION_ALTITUDE_KM, MISSIONS_FILE,
                               PARKING_ALTITUDE_KM, SHIP_NAME)
from app_ursina.entities import BodyEntity, SizeMode, SpaceshipEntity
from app_ursina.geometry import vec3_to_scene
from app_ursina.hud import HudMixin
from app_ursina.menus import MenuMixin
from app_ursina.missions import MissionMixin


class SolaraApp(MissionMixin, HudMixin, MenuMixin, Entity):
    """Owns simulation time, body entities, HUD and input handling."""

    def __init__(self,
                 ephemeris: JplEphemeris,
                 bodies: dict[str, CelestialBody],
                 epoch: datetime) -> None:
        super().__init__()
        self.ephemeris: JplEphemeris = ephemeris
        self.bodies: dict[str, CelestialBody] = bodies
        self.epoch: datetime = epoch
        self.sim_time_s: float = 0.0
        self.time_step_index: int = DEFAULT_TIME_STEP_INDEX
        self.auto_play: bool = False
        self.play_direction: float = 1.0
        self.size_mode: SizeMode = SizeMode.LOG
        # The craft is followable too (tab / double-click / on mission load).
        self.follow_names: list[str] = list(bodies.keys()) + [SHIP_NAME]
        self.follow_index: int = 0
        self.body_entities: dict[str, BodyEntity] = {
            name: BodyEntity(name, body, is_star=(name == "Sun"))
            for name, body in bodies.items()
        }
        self._draw_orbit_lines()
        self._setup_lighting()
        self.planner: MissionPlanner = MissionPlanner(ephemeris=ephemeris,
                                                      mu=MU_SUN)
        self.missions: dict[str, HistoricalMission] = load_missions(path=MISSIONS_FILE)
        self.mission_label: str = ""
        # Historical-mission replay state (a real craft coasting under full
        # N-body gravity). Distinct from the planned FLY_TO missions.
        self.historical_active: bool = False
        # Reactionless "test" drive for FLY_TO craft: thrust without spending
        # mass, so any mission is reachable and captures never run dry.
        self.use_test_ship: bool = False
        # Earth-Moon round-trip state (scripted burns: return at the Moon,
        # then circularize back in low Earth orbit so it clearly comes home).
        self.moon_trip: bool = False
        self._moon_return_at: float = 0.0
        self._moon_returning: bool = False
        self._moon_descending: bool = False
        self._moon_arrived: bool = False
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
        self.ships: dict[str, SpaceshipEntity] = {SHIP_NAME: SpaceshipEntity(name=SHIP_NAME)}
        self.sim_ship: Spaceship | None = None
        self.parked: bool = True
        self._sync_bodies_to_time(time_s=self.sim_time_s)
        self.camera_rig: EditorCamera = EditorCamera(rotation_smoothing=2,
                                                     pan_speed=Vec2(2, 2),
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
        self.date_text: Text = Text(text="",
                                    position=(-0.85, 0.47),
                                    scale=0.9)
        self.status_text: Text = Text(text="",
                                      position=(-0.85, 0.43),
                                      scale=0.8,
                                      color=ursina_color.yellow)
        self.follow_text: Text = Text(text="",
                                      position=(-0.85, 0.39),
                                      scale=0.8,
                                      color=ursina_color.green)
        self.mission_text: Text = Text(text="",
                                       position=(-0.85, 0.35),
                                       scale=0.8,
                                       color=ursina_color.azure)
        self.note_text: Text = Text(text="",
                                    position=(-0.85, 0.31),
                                    scale=0.75,
                                    color=ursina_color.white)
        # Flight-plan panel ('i'): what the craft has done / is doing / will do.
        self.show_plan: bool = False
        self.plan_text: Text = Text(text="",
                                    position=(-0.85, 0.22),
                                    scale=0.7,
                                    origin=(-0.5, 0.5),
                                    color=ursina_color.white,
                                    enabled=False)
        self.help_text: Text = Text(
            text="space play | arrows step/timestep | dbl-click/tab follow | m sizes | r reverse | "
                 "h start at | f fly to | v mission | t test drive | i plan | e export | esc reset",
            position=(-0.85, -0.47),
            scale=0.7,
            color=ursina_color.white66)
        self._label_targets: list[tuple[Text, Entity, str]] = []
        for name, entity in self.body_entities.items():
            self._label_targets.append((Text(text=name,
                                             scale=0.7,
                                             origin=(0, 0),
                                             color=ursina_color.white),
                                        entity,
                                        name))
        for name, ship in self.ships.items():
            self._label_targets.append((Text(text=name,
                                             scale=0.7,
                                             origin=(0, 0),
                                             color=ursina_color.azure),
                                        ship,
                                        name))
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

    def advance(self,
                dt_s: float) -> None:
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
            self._sync_bodies_to_time(time_s=self.sim_time_s)
            self._advance_ship(dt_s)
        if self.moon_trip:
            if self._moon_returning and self.sim_time_s >= self._moon_return_at:
                self._moon_return_burn()
                self._moon_returning = False
            elif not self._moon_returning and not self._moon_arrived:
                # Circularize at the first perigee after the return burn — robust
                # to however large the (slingshot-perturbed) return ellipse is.
                relative_position: Vec3 = self.sim_ship.position - self.bodies["Earth"].position
                relative_velocity: Vec3 = self.sim_ship.velocity - self.bodies["Earth"].velocity
                range_rate: float = relative_position.dot(other=relative_velocity)
                if range_rate < 0.0:
                    self._moon_descending = True
                elif self._moon_descending:
                    self._moon_circularize_burn()
                    self._moon_arrived = True
        self.refresh_positions()
        self.refresh_hud()

    def _advance_historical(self,
                            dt_s: float) -> None:
        """Coast a real craft forward under full N-body gravity (adaptive)."""
        advance_coasting(ship=self.sim_ship,
                         ephemeris=self.ephemeris,
                         bodies=self.bodies,
                         time_s=self.sim_time_s,
                         dt_s=dt_s)
        self.sim_time_s += dt_s
        self._sync_bodies_to_time(time_s=self.sim_time_s)

    def _advance_mission(self,
                         dt_s: float) -> None:
        fine_chunk: float = self.sim_ship.max_integration_dt
        remaining: float = dt_s
        while remaining > 1e-6:
            target: CelestialBody = self.bodies[self.mission_target]
            distance: float = (self.sim_ship.position - target.position).magnitude()
            # Re-sync the target on a cadence that tightens as the craft
            # closes in (its position must be fresh during the approach and
            # capture, but daily is plenty out in the cruise). A gradual
            # far -> approach -> near refinement avoids a coarse step
            # overshooting the sensitive approach with a stale planet.
            cap: float = self.mission_capture_km
            chunk: float
            if distance <= 4.0 * cap:
                chunk = fine_chunk          # capture: every sub-step
            elif distance <= 20.0 * cap:
                chunk = 3600.0              # approach: hourly
            else:
                chunk = 86400.0             # cruise: daily
            step: float = min(chunk, remaining)
            self.sim_time_s += step
            for name, body in self.mission_gravity_bodies.items():
                position, velocity = self.ephemeris.state(body=name,
                                                          time_s=self.sim_time_s)
                body.position = position
                body.velocity = velocity
            self.sim_ship.step_forward(dt=step,
                                       bodies=self.mission_gravity_bodies)
            self._maybe_correct_course()
            remaining -= step
        # Re-sync everything for rendering at the final time.
        self._sync_bodies_to_time(time_s=self.sim_time_s)

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
        body: CelestialBody = self.bodies[self.home_body]
        orbit_radius: float = body.radius + PARKING_ALTITUDE_KM
        angular_rate: float = circular_orbit_velocity(body_mass=body.mass,
                                                      orbit_radius_km=orbit_radius) / orbit_radius
        angle: float = angular_rate * self.sim_time_s
        offset: Vec3 = Vec3(x=orbit_radius * cos(angle),
                            y=orbit_radius * sin(angle),
                            z=0.0)
        return body.position + offset

    def _sync_bodies_to_time(self,
                             time_s: float) -> None:
        """Move the body objects to their ephemeris state, for live gravity."""
        for name, body in self.bodies.items():
            position, velocity = self.ephemeris.state(body=name,
                                                      time_s=time_s)
            body.position = position
            body.velocity = velocity

    def _advance_ship(self,
                      dt_s: float) -> None:
        """
        While parked the craft is kinematic (placed in refresh_positions),
        so there is nothing to integrate. During a mission the simulated
        craft flies patched-conic (Sun + target): forward steps simulate
        and sub-step, backward steps replay history.
        """
        if self.parked or self.sim_ship is None or dt_s == 0.0:
            return
        if dt_s > 0.0:
            self.sim_ship.step_forward(dt=dt_s,
                                       bodies=self.mission_gravity_bodies)
        else:
            self.sim_ship.step_backwards()

    def _set_home(self,
                  body: str) -> None:
        """Park the craft around `body`, ending any active mission."""
        self._close_menus()
        self.home_body = body
        self.parked = True
        self.sim_ship = None
        self.mission_active = False
        self.historical_active = False
        self.moon_trip = False
        self.mission_label = ""
        self.ships[SHIP_NAME].set_color(color=ursina_color.azure)
        self.ships[SHIP_NAME].trail.clear()
        self.follow(name=body)
        self.refresh_positions()
        self.refresh_hud()

    # ------------------------------------------------------------------
    # Camera / following
    # ------------------------------------------------------------------

    def _follow_entity(self) -> SpaceshipEntity | BodyEntity:
        """The entity currently followed (a body or the craft)."""
        name: str = self.follow_names[self.follow_index]
        if name == SHIP_NAME:
            return self.ships[SHIP_NAME]
        return self.body_entities[name]

    def _reset_camera(self) -> None:
        self.follow_index = 0   # the Sun is first in the dict
        self.camera_rig.rotation_x = DEFAULT_CAMERA_PITCH
        self.camera_rig.rotation_y = 0.0
        camera.z = DEFAULT_CAMERA_Z
        self.camera_rig.target_z = DEFAULT_CAMERA_Z
        self.camera_rig.position = self._follow_entity().position

    def follow(self,
               name: str) -> None:
        if name in self.follow_names:
            self.follow_index = self.follow_names.index(name)
            self.refresh_positions()
            self.refresh_hud()

    # ------------------------------------------------------------------
    # Scene setup
    # ------------------------------------------------------------------

    def _setup_lighting(self) -> None:
        """A point light at the Sun (origin) plus faint ambient fill."""
        self.sun_light: PointLight = PointLight(parent=scene,
                                                position=(0, 0, 0),
                                                color=ursina_color.white)
        self.ambient: AmbientLight = AmbientLight(color=ursina_color.rgba(r=0.18,
                                                                          g=0.18,
                                                                          b=0.22,
                                                                          a=1.0))

    def _draw_orbit_lines(self) -> None:
        """One faint line per body that orbits the Sun directly."""
        for name, body in self.bodies.items():
            if body.parent_body != "Sun" or body.orbital_period <= 0:
                continue
            period_s: float = body.orbital_period * 86400.0
            points: list = []
            for i in range(ORBIT_SAMPLES + 1):
                t: float = self.sim_time_s + period_s * i / ORBIT_SAMPLES
                position, _ = self.ephemeris.state(body=name,
                                                   time_s=t)
                points.append(vec3_to_scene(position))
            Entity(model=Mesh(vertices=points,
                              mode="line",
                              thickness=1),
                   color=ursina_color.rgba(r=1,
                                           g=1,
                                           b=1,
                                           a=0.15),
                   unlit=True)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def refresh_positions(self) -> None:
        for name, entity in self.body_entities.items():
            position, _ = self.ephemeris.state(body=name,
                                               time_s=self.sim_time_s)
            entity.update_from_state(position_km=position)
            entity.update_spin(time_s=self.sim_time_s)
        # Parked: kinematic parking orbit. Mission: the simulated craft.
        ship_position: Vec3 = (self._parking_position()
                               if self.parked
                               else self.sim_ship.position)
        self.ships[SHIP_NAME].sync(position_km=ship_position)
        self.camera_rig.position = self._follow_entity().position

    def apply_visual_sizes(self) -> None:
        """Per-frame: bodies' apparent sizes depend on camera distance."""
        cam = camera.world_position
        for entity in self.body_entities.values():
            distance = (entity.world_position - cam).length()
            entity.apply_size(mode=self.size_mode,
                              camera_distance=distance)
        for ship in self.ships.values():
            ship.apply_size(camera_distance=(ship.world_position - cam).length())

    # ------------------------------------------------------------------
    # Per-frame update and input (called by ursina)
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.auto_play:
            self.advance(dt_s=self.time_step_s * self.play_direction)
        self.apply_visual_sizes()
        self.update_labels()
        if self.show_plan:
            self._refresh_plan_panel()

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
            self.size_mode = (SizeMode.REAL
                              if self.size_mode is SizeMode.LOG
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
            self._notify(message=f"Test drive (reactionless) "
                         f"{'ON' if self.use_test_ship else 'OFF'} — applies to the next FLY_TO.")
            self.refresh_hud()
        elif key == "i":
            self.show_plan = not self.show_plan
            self.plan_text.enabled = self.show_plan
            if self.show_plan:
                self._refresh_plan_panel()
        elif key == "e":
            self._export_trajectory()
        elif key in ("right arrow", "right arrow hold"):
            self.advance(dt_s=self.time_step_s)
        elif key in ("left arrow", "left arrow hold"):
            self.advance(dt_s=-self.time_step_s)
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
    app = Ursina(title="Solara",
                                 borderless=False)
    window.color = ursina_color.black
    epoch: datetime = datetime.now()
    kernel: SPK = SPK.open(path=EPHEMERIS_FILE)
    bodies: dict[str, CelestialBody] = load_bodies_from_json()
    ephemeris: JplEphemeris = JplEphemeris.from_bodies(kernel=kernel,
                                                       bodies=bodies,
                                                       epoch_jd=convert_to_julian_date(date=epoch))
    SolaraApp(ephemeris=ephemeris,
              bodies=bodies,
              epoch=epoch)
    try:
        app.run()
    finally:
        kernel.close()
