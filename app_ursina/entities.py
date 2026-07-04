from ursina.texture import Texture


from ursina.texture import Texture


from __future__ import annotations
from enum import Enum, auto
from app_ursina.config import MARKER_APPARENT_SIZE, SATURN_RING_TEXTURE, SHIP_RADIUS_KM
from app_ursina.geometry import (hex_to_color, log_diameter, make_ring_mesh,
                                 real_diameter, vec3_to_scene)
from app_ursina.textures import load_body_texture, load_texture_file
from core.bodies import CelestialBody
from core.trail import TrailPath
from core.vec3 import Vec3
from ursina.entity import Entity
from ursina.vec3 import Vec3
from ursina.entity import Entity
from ursina.color import Color
from ursina.entity import Entity
from ursina import Entity, Mesh, color as ursina_color


class SizeMode(Enum):
    LOG = auto()    # logarithmic, everything visible at once
    REAL = auto()   # true radii, with markers for sub-pixel bodies


class BodyEntity(Entity):
    """
    A celestial body. The `BodyEntity` itself is the position + axial-tilt
    frame; its child `globe` carries the textured sphere and spins about the
    (tilted) polar axis. Rings sit in the equatorial plane (children of the
    globe, so they share the tilt), and a fixed-apparent-size marker dot
    stands in when the real sphere is sub-pixel.
    """
    def __init__(self,
                 name: str,
                 body: CelestialBody,
                 is_star: bool) -> None:
        super().__init__()                       # bare position + tilt frame
        self.body: CelestialBody = body
        self.body_name: str = name
        self.body_color: Color = hex_to_color(hex_color=body.color)
        self.rotation_z: float = body.axial_tilt_deg   # axial tilt (obliquity)
        # The visible, spinning sphere. With a surface texture the colour is
        # white (no tint) so the map shows true; otherwise fall back to the
        # body's flat colour. It carries the collider + body_name so clicking
        # the planet follows it.
        texture: Texture | None = load_body_texture(body.texture)
        self.globe: Entity = Entity(parent=self,
                                    model="sphere",
                                    texture=texture,
                                    color=ursina_color.white if texture else self.body_color,
                                    scale=log_diameter(radius_km=body.radius),
                                    collider="sphere",
                                    unlit=is_star)   # star is its own light; planets are lit
        self.globe.body_name = name
        if body.rings > 0:
            self._add_rings(ring_value=body.rings)
        # A fixed-apparent-size dot shown only when the real sphere is
        # smaller than it (REAL mode, zoomed out).
        self.marker: Entity = Entity(model="sphere",
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
            inner, outer, ring_color = 0.7, 1.5, ursina_color.rgba(r=0.82,
                                                                   g=0.72,
                                                                   b=0.55,
                                                                   a=0.7)
            # Use the real ring texture (with alpha for the gaps) when present.
            ring_texture: Texture | None = load_texture_file(filename=SATURN_RING_TEXTURE)
            if ring_texture is not None:
                Entity(parent=self.globe,
                       model=make_ring_mesh(inner, outer),
                       texture=ring_texture,
                       color=ursina_color.white,
                       double_sided=True,
                       unlit=True)
                return
        else:                      # Jupiter / Uranus / Neptune: faint
            inner, outer, ring_color = 0.65, 1.05, ursina_color.rgba(0.8,
                                                                     g=0.82,
                                                                     b=0.85,
                                                                     a=0.18)
        Entity(parent=self.globe,
               model=make_ring_mesh(inner, outer),
               color=ring_color,
               double_sided=True,
               unlit=True)

    def update_from_state(self,
                          position_km: Vec3) -> None:
        self.position: Vec3 = vec3_to_scene(v=position_km)
        self.marker.position = self.position

    def update_spin(self,
                    time_s: float) -> None:
        """Rotate the globe about its (tilted) polar axis for the given time."""
        period: float = self.body.rotation_period
        if period > 0:
            self.globe.rotation_y = (time_s / period * 360.0) % 360.0

    def apply_size(self,
                   mode: SizeMode,
                   camera_distance: float) -> None:
        """Resize the sphere/marker for the current mode and zoom level."""
        if mode is SizeMode.LOG:
            self.globe.scale = log_diameter(radius_km=self.body.radius)
            self.marker.enabled = False
        else:
            diameter: float = real_diameter(radius_km=self.body.radius)
            self.globe.scale = diameter
            marker_size: float = camera_distance * MARKER_APPARENT_SIZE
            self.marker.world_scale = marker_size
            self.marker.enabled = diameter < marker_size


class TrailEntity:
    """Renders a craft's growing trajectory as a decimated line."""
    def __init__(self,
                 color: Color,
                 min_separation_km: float,
                 max_points: int) -> None:
        self.path: TrailPath = TrailPath(min_separation_km=min_separation_km,
                                         max_points=max_points)
        self.entity: Entity = Entity(model=Mesh(vertices=[],
                                                mode="line",
                                                thickness=2),
                                     color=color,
                                     unlit=True)

    def record(self,
               position_km: Vec3) -> None:
        if self.path.add(point=position_km) and len(self.path) >= 2:
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
        super().__init__(model="sphere",
                         color=color,
                         scale=real_diameter(radius_km=SHIP_RADIUS_KM),
                         unlit=True)
        self.craft_name: str = name
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
