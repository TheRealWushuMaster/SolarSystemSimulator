from __future__ import annotations

import tkinter.font as tkfont
from typing import Any
from .settings import DRAW_3D, CANVAS_DRAW_PADDING, SPACESHIP_COLOR, SPACESHIP_BORDER, \
    BODY_NAME_COLOR, DEFAULT_FONT, TEXT_SIZE_NAME, DEFAULT_NAME_TEXT_PADDING, ORBIT_FILL_COLOR
from .functions import get_lighter_color


def update_standard_draw_scale(self: Any, width: float, height: float) -> None:
    if not DRAW_3D:
        self.standard_draw_scale = min(
            (width - CANVAS_DRAW_PADDING) / self.max_distance_width,
            (height - CANVAS_DRAW_PADDING) / self.max_distance_height,
        ) / 2
    else:
        self.standard_draw_scale = min(
            (width - CANVAS_DRAW_PADDING) / self.max_distance_width,
            (height - CANVAS_DRAW_PADDING) / self.max_distance_height,
            (height - CANVAS_DRAW_PADDING) / self.max_distance_depth,
        ) / 2


def draw_celestial_bodies(self: Any) -> None:
    self.body_ids = []
    clear_canvas_bodies(self)
    draw_orbits(self)
    for body in self.simulation.celestial_bodies.values():
        x = body.x - self.simulation.origin.x
        y = body.y - self.simulation.origin.y
        z = body.z - self.simulation.origin.z
        radius = max(round(body.radius * self.distance_scale), 1)
        if DRAW_3D:
            (x, y, z) = (x, y, z) @ self.rotation_matrix
        x, y = transform_coordinates_to_pixels(self, x, y)
        body_id = self.widgets.canvas.create_oval(
            x-radius, y-radius, x+radius, y+radius,
            fill=body.color, outline=get_lighter_color(body.color), tags='object',
        )
        if radius > 3 and body.rings > 0:
            draw_planetary_rings(self, x, y, radius, body.rings)
            self.widgets.canvas.create_arc(
                x-radius, y-radius, x+radius, y+radius,
                fill=body.color, outline=get_lighter_color(body.color),
                start=0, extent=180, tags='object',
            )
            self.widgets.canvas.create_arc(
                x-(radius-1), y-(radius-1), x+(radius-1), y+(radius-1),
                fill=body.color, outline=body.color, start=0, extent=180, tags='object',
            )
        text_id = place_name(self, x, y, radius, body.name)
        self.body_ids.append((body.name, body_id, text_id))
    if self.simulation.have_spaceships:
        for spaceship_name, spaceship in self.simulation.spaceships.items():
            spaceship_id, text_id = draw_spaceship(self, spaceship_name, spaceship)
            self.body_ids.append((spaceship_name, spaceship_id, text_id))
    bring_hud_to_foreground(self)


def bring_hud_to_foreground(self: Any) -> None:
    for obj in self.hud_objects:
        self.widgets.canvas.lift(obj)


def clear_canvas_bodies(self: Any) -> None:
    for tag in ('object', 'object_text', 'planet_rings', 'orbit', 'spaceship', 'trajectory'):
        objects = self.widgets.canvas.find_withtag(tag)
        for obj in objects:
            self.widgets.canvas.delete(obj)


def transform_coordinates_to_pixels(self: Any, x: float, y: float) -> tuple[int, int]:
    x_p = round(x * self.distance_scale + self.center_point_x)
    y_p = round(y * self.distance_scale + self.center_point_y)
    return x_p, y_p


def transform_pixels_to_coordinates(self: Any, x: float, y: float) -> tuple[float, float]:
    x_c = x / self.distance_scale
    y_c = y / self.distance_scale
    return x_c, y_c


def draw_spaceship(self: Any, spaceship_name: str, spaceship: Any) -> tuple[int, int]:
    x = spaceship.x - self.simulation.origin.x
    y = spaceship.y - self.simulation.origin.y
    z = spaceship.z - self.simulation.origin.z
    if DRAW_3D:
        (x, y, z) = (x, y, z) @ self.rotation_matrix
    x, y = transform_coordinates_to_pixels(self, x, y)
    radius = max(round(spaceship.size * self.distance_scale), 1)
    spaceship_id: int = self.widgets.canvas.create_oval(
        x-radius, y-radius, x+radius, y+radius,
        fill=SPACESHIP_COLOR, outline=SPACESHIP_BORDER, tags='spaceship',
    )
    text_id: int = place_name(self, x, y, radius, spaceship_name)
    return spaceship_id, text_id


def text_object_size(text: str, font: str, font_size: int) -> tuple[int, int]:
    f = tkfont.Font(family=font, size=font_size)
    text_width: int = f.measure(text)
    text_height: int = f.metrics("linespace")
    return text_width, text_height


def place_name(self: Any, center_x: int, center_y: int, radius: int, name: str) -> int:
    x, y, anchor = find_name_text_position(self, name, center_x, center_y, radius)
    text_id: int = self.widgets.canvas.create_text(
        x, y, anchor=anchor, text=name,
        fill=BODY_NAME_COLOR, font=(DEFAULT_FONT, TEXT_SIZE_NAME), tags='object_text',
    )
    return text_id


def find_name_text_position(
    self: Any, name: str, center_x: int, center_y: int, planet_radius: int,
    padding: int = DEFAULT_NAME_TEXT_PADDING,
) -> tuple[float, float, str]:
    text_width, text_height = text_object_size(name, DEFAULT_FONT, TEXT_SIZE_NAME)
    default_position: tuple[float, float, str] = (center_x + planet_radius + padding, center_y, "w")
    positions: list[tuple[float, float, str]] = [
        default_position,
        (center_x - planet_radius - padding, center_y, "e"),
        (center_x, center_y - planet_radius - padding, "s"),
        (center_x, center_y + planet_radius + padding, "n"),
        (center_x - planet_radius - padding, center_y - planet_radius - padding, "se"),
        (center_x - planet_radius - padding, center_y + planet_radius + padding, "ne"),
        (center_x + planet_radius + padding, center_y - planet_radius - padding, "sw"),
        (center_x + planet_radius + padding, center_y + planet_radius + padding, "nw"),
    ]
    least_overlap = -1.0
    least_overlap_position = default_position
    for position in positions:
        overlap = collision_with_other_body_names(self, text_width, text_height, position)
        if overlap > 0:
            if least_overlap > -1:
                if least_overlap > overlap:
                    least_overlap_position = position
                    least_overlap = overlap
            else:
                least_overlap = overlap
                least_overlap_position = position
        else:
            if text_is_within_canvas(self, text_width, text_height, position):
                return position
    return least_overlap_position


def collision_with_other_body_names(
    self: Any,
    width: int,
    height: int,
    position: tuple[float, float, str],
) -> float:
    x_new, y_new, a = position
    if a == "w":    x = x_new;              y = y_new - round(height/2)
    elif a == "e":  x = x_new - width;      y = y_new - round(height/2)
    elif a == "s":  x = x_new - round(width/2); y = y_new - height
    elif a == "n":  x = x_new - round(width/2); y = y_new
    elif a == "se": x = x_new - width;      y = y_new - height
    elif a == "ne": x = x_new - width;      y = y_new
    elif a == "sw": x = x_new;              y = y_new - height
    elif a == "nw": x = x_new;              y = y_new
    else:           x = x_new;              y = y_new
    max_overlap = 0.0
    for body_name, body_id, text_id in self.body_ids:
        text_bbox = self.widgets.canvas.bbox(text_id)
        body_bbox = self.widgets.canvas.bbox(body_id)
        if text_bbox is None or body_bbox is None:
            return 0.0
        overlap = max(
            overlap_with_bbox(x, y, width, height, text_bbox),
            overlap_with_bbox(x, y, width, height, body_bbox),
        )
        if overlap > max_overlap:
            max_overlap = overlap
    return max_overlap


def overlap_with_bbox(
    x1: float, y1: float, width: float, height: float,
    other_bbox: tuple[float, float, float, float],
) -> float:
    x2, y2, x2w, y2h = other_bbox
    Cx1 = x1 <= x2 <= x1 + width
    Cx2 = x2 <= x1 <= x2w
    Cy1 = y1 <= y2 <= y1 + height
    Cy2 = y2 <= y1 <= y2h
    if Cx1 and Cy1:
        return min((x2 - (x1+width)), x2w-x2, width) * min((y2 - (y1+height)), y2h, height)
    elif Cx1 and Cy2:
        return min((x2 - (x1+width)), x2w-x2, width) * min((y1 - y2h), y2h, height)
    elif Cx2 and Cy1:
        return min((x1 - x2w), x2w-x2, width) * min((y2 - (y1+height)), y2h, height)
    elif Cx2 and Cy2:
        return min((x1 - x2w), x2w-x2, width) * min((y1 - y2h), y2h, height)
    else:
        return 0.0


def text_is_within_canvas(
    self: Any, width: float, height: float, position: tuple[float, float, str]
) -> bool:
    x, y, anchor = position
    if "w" in anchor:    # To the right of the position
        if not (x+width <= self.widgets.canvas.winfo_width()
                and round(y-height/2) >= 0
                and round(y+height/2) <= self.widgets.canvas.winfo_height()):
            return False
    if "e" in anchor:    # To the left of the position
        if not (x-width >= 0
                and round(y-height/2) >= 0
                and round(y+height/2) <= self.widgets.canvas.winfo_height()):
            return False
    if "s" in anchor:    # On top of the position
        if not (y-height >= 0
                and round(x-width/2) >= 0
                and round(x+width/2) <= self.widgets.canvas.winfo_width()):
            return False
    if "n" in anchor:    # Below the position
        if not (y+height <= self.widgets.canvas.winfo_height()
                and round(x-width/2) >= 0
                and round(x+width/2) <= self.widgets.canvas.winfo_width()):
            return False
    return True


def draw_planetary_rings(self: Any, x: int, y: int, planet_radius: int, ring_value: int) -> None:
    ring_size = planet_radius * 1.5
    ring_thickness = max(round(planet_radius / 30 * ring_value), 1)
    if ring_value == 3:
        ring_thickness *= 2
        ring_colors = ['#1a1917', '#5c5344', '#232220', '#4e473f']
        for i, color in enumerate(ring_colors):
            draw_one_ring(self, x, y, planet_radius, ring_size + i * ring_thickness, color, ring_thickness)
    else:
        draw_one_ring(self, x, y, planet_radius, ring_size, "lightgray", ring_thickness)


def draw_one_ring(self: Any, x: int, y: int, planet_radius: int,
                  ring_size: float, ring_color: str, ring_thickness: int) -> None:
    self.widgets.canvas.create_oval(
        x - ring_size, y - round(planet_radius/2),
        x + ring_size, y + round(planet_radius/2),
        outline=ring_color, width=ring_thickness, tags='planet_rings',
    )


def update_distance_scale(self: Any) -> None:
    self.distance_scale = self.standard_draw_scale * self.modified_scale
    self.update_scale_text()


def draw_orbits(self: Any) -> None:
    for body_name, body in self.simulation.celestial_bodies.items():
        for i in range(len(body.orbit_points) - 1):
            x1 = body.orbit_points[i][0] - self.simulation.origin.x
            y1 = body.orbit_points[i][1] - self.simulation.origin.y
            x2 = body.orbit_points[i+1][0] - self.simulation.origin.x
            y2 = body.orbit_points[i+1][1] - self.simulation.origin.y
            if DRAW_3D:
                z1 = body.orbit_points[i][2] - self.simulation.origin.z
                z2 = body.orbit_points[i+1][2] - self.simulation.origin.z
                (x1, y1, z1) = (x1, y1, z1) @ self.rotation_matrix
                (x2, y2, z2) = (x2, y2, z2) @ self.rotation_matrix
            x1, y1 = transform_coordinates_to_pixels(self, x1, y1)
            x2, y2 = transform_coordinates_to_pixels(self, x2, y2)
            self.widgets.canvas.create_line(x1, y1, x2, y2, fill=ORBIT_FILL_COLOR, dash=(2, 2), tags='orbit')


def draw_spaceship_trajectory(self: Any, spaceship_positions: list[Any], trajectory_color: str) -> None:
    for i, position in enumerate(spaceship_positions):
        if i > 0:
            x1 = spaceship_positions[i-1].x - self.simulation.origin.x
            y1 = spaceship_positions[i-1].y - self.simulation.origin.y
            z1 = spaceship_positions[i-1].z - self.simulation.origin.z
            x2 = position.x - self.simulation.origin.x
            y2 = position.y - self.simulation.origin.y
            z2 = position.z - self.simulation.origin.z
            (x1, y1, z1) = (x1, y1, z1) @ self.rotation_matrix
            (x2, y2, z2) = (x2, y2, z2) @ self.rotation_matrix
            x1, y1 = transform_coordinates_to_pixels(self, x1, y1)
            x2, y2 = transform_coordinates_to_pixels(self, x2, y2)
            self.widgets.canvas.create_line(x1, y1, x2, y2,
                                            fill=trajectory_color, dash=(2, 2), tags='trajectory')
