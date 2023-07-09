from settings import *
import customtkinter as ctk
import tkinter.font as tkfont
import requests
import os
import email.utils
import classes
from jplephem.spk import SPK
import datetime
from functions import get_lighter_color, format_with_thousands_separator, property_name_and_units
from math import sqrt
from numpy import array, eye, sin, cos

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.widgets = self.configure_app_window()
        self.configure_canvas_hud()
        self.bind_events()
        self.check_ephemeris_file_update()
        self.load_ephemeris_data()

        self.celestial_bodies = self.create_bodies()
        
        self.date = datetime.datetime.now()
        self.timestamp_days = 0
        self.timestamp_months = 0
        self.timestamp_years = 0
        self.timestamp = self.convert_to_julian_date()
        self.update_time_text()

        self.update_following_object()
        self.load_orbits()
        self.update_all_bodies_positions()
        self.update_boundaries()

        self.modified_scale = 1.0
        self.center_point_x, self.center_point_y = round(self.widgets.canvas.winfo_reqwidth()/2), round(self.widgets.canvas.winfo_reqheight()/2)
        self.update_standard_draw_scale(self.widgets.canvas.winfo_reqwidth(), self.widgets.canvas.winfo_reqheight())
        self.update_distance_scale()
        self.rotation_matrix = eye(3)
        self.draw_celestial_bodies()

    def configure_app_window(self):
        self.title("Solar System Simulator")
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.resizable=(True, True)
        self.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])
        self.iconbitmap("logos/logo-2.ico")
        self.configure(fg_color = DEFAULT_BACKGROUND)
        widgets = Widgets(self)
        return widgets

    def configure_canvas_hud(self):
        self.time_text = self.widgets.canvas.create_text(10, 10, anchor="nw", fill=DEFAULT_FONT_COLOR, font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.scale_text = self.widgets.canvas.create_text(10, 10+INFO_TEXT_SEPARATION, anchor="nw", fill=SCALE_TEXT_COLOR, text="Scale", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.distance_text_km = self.widgets.canvas.create_text(10, 10+2*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Distance km", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.distance_text_au = self.widgets.canvas.create_text(10, 10+3*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Distance AU", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.following_object = self.widgets.canvas.create_text(10, 10+4*INFO_TEXT_SEPARATION, anchor="nw", fill=FOLLOWING_OBJECT_TEXT_COLOR, text="Following: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.following_object_info = self.widgets.canvas.create_text(10, 10+5*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Object info: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.hud_objects = (self.time_text, self.scale_text, self.distance_text_km,
                            self.distance_text_au, self.following_object, self.following_object_info)

    def bind_events(self):
        self.widgets.canvas.bind("<Configure>", self.on_canvas_resize)
        self.widgets.canvas.bind("<MouseWheel>", self.modify_zoom_level)
        self.widgets.canvas.bind("<Motion>", self.mouse_hover)
        self.widgets.canvas.bind("<Double-Button-1>", self.handle_canvas_double_click)
        self.widgets.canvas.bind("<ButtonPress-1>", self.start_mouse_drag)
        self.widgets.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.widgets.canvas.bind("<ButtonRelease-1>", self.release_mouse_drag)
        self.bind("<Escape>", self.reset_view)
        self.bind("<Left>", self.handle_time_adjustment)
        self.bind("<Right>", self.handle_time_adjustment)

    def check_ephemeris_file_update(self):
        if os.path.exists(EPHEMERIS_FILE):
            current_timestamp = os.path.getmtime(EPHEMERIS_FILE)
        else:
            current_timestamp = 0
        response = requests.head(EPHEMERIS_URL)
        if 'Last-Modified' in response.headers:
            latest_timestamp = response.headers['Last-Modified']
        else:
            latest_timestamp = 0
        latest_timestamp = email.utils.mktime_tz(email.utils.parsedate_tz(latest_timestamp))
        if current_timestamp < latest_timestamp:
            print("Downloading updated ephemeris file...")
            self.download_updated_ephemeris()
            print("Ephemeris file has been downloaded.")
        else:
            print("Ephemeris file is up to date.")

    def download_updated_ephemeris(self):
        response = requests.get(EPHEMERIS_URL)
        with open(EPHEMERIS_FILE, "wb") as file:
            file.write(response.content)

    def load_ephemeris_data(self):
        self.kernel = SPK.open('de421.bsp')

    def close_ephemeris_data(self):
        self.kernel.close()

    def create_bodies(self, stars=True, planets=True, moons=True):
        celestial_bodies = {}
        if stars:
            celestial_bodies.update(self.create_body_of_a_class(Star_data, classes.Star))
        if planets:
            celestial_bodies.update(self.create_body_of_a_class(Planet_data, classes.Planet))
        if moons:
            celestial_bodies.update(self.create_body_of_a_class(Moon_data, classes.Planet))
        return celestial_bodies

    def create_body_of_a_class(self, body_data, body_class):
        bodies = {}
        for name, properties in body_data.items():
                body = body_class(name, **properties)
                bodies[name] = body
        return bodies

    def start_mouse_drag(self, event):
        self.mouse_drag_starting_point = (event.x, event.y)

    def on_mouse_drag(self, event):
        if self.mouse_drag_starting_point is None:
            return
        delta_x = event.x - self.mouse_drag_starting_point[0]
        delta_y = event.y - self.mouse_drag_starting_point[1]
        rotation_angle_x = delta_y * 0.01  # Adjust sensitivity as needed
        rotation_angle_z = delta_x * 0.01  # Adjust sensitivity as needed
        rotation_matrix_x = array([[1, 0, 0],
                                   [0, cos(rotation_angle_x), -sin(rotation_angle_x)],
                                   [0, sin(rotation_angle_x), cos(rotation_angle_x)]])
        rotation_matrix_y = array([[cos(rotation_angle_z), 0, sin(rotation_angle_z)],
                                   [0, 1, 0],
                                   [-sin(rotation_angle_z), 0, cos(rotation_angle_z)]])
        rotation_matrix_z = array([[cos(rotation_angle_z), -sin(rotation_angle_z), 0],
                                   [sin(rotation_angle_z), cos(rotation_angle_z), 0],
                                   [0, 0, 1]])
        self.rotation_matrix = rotation_matrix_x @ rotation_matrix_z @ self.rotation_matrix
        self.mouse_drag_starting_point = (event.x, event.y)
        self.draw_celestial_bodies()

    def release_mouse_drag(self, event):
        self.mouse_drag_starting_point = None

    def reset_view(self, event):
        self.rotation_matrix = eye(3)
        self.modified_scale = 1.0
        self.update_distance_scale()
        self.draw_celestial_bodies()

    def update_standard_draw_scale(self, width, height):
        if not DRAW_3D:
            self.standard_draw_scale = min((width-CANVAS_DRAW_PADDING)/self.max_distance_width, (height-CANVAS_DRAW_PADDING)/self.max_distance_height)/2
        else:
            # TO DO: adjust the scale in relation to rotation angle
            self.standard_draw_scale = min((width-CANVAS_DRAW_PADDING)/self.max_distance_width, (height-CANVAS_DRAW_PADDING)/self.max_distance_height, (height-CANVAS_DRAW_PADDING)/self.max_distance_depth)/2

    def draw_celestial_bodies(self):
        self.body_ids = []
        self.clear_canvas_bodies()
        self.draw_orbits()
        for body in self.celestial_bodies.values():
            x, y, z = body.x - self.origin.x, body.y - self.origin.y, body.z - self.origin.z
            radius = max(round(body.radius * self.distance_scale), 1)
            if DRAW_3D:
                (x, y, z) = (x, y, z) @ self.rotation_matrix
            x, y = self.transform_coordinates_to_pixels(x, y)
            body_id = self.widgets.canvas.create_oval(x-radius, y-radius, x + radius, y + radius, fill=body.color, outline=get_lighter_color(body.color), tags='object')
            if radius > 3 and body.rings > 0:
                self.draw_planetary_rings(x, y, radius, body.rings)
                self.widgets.canvas.create_arc(x-radius, y-radius, x + radius, y + radius, fill=body.color, outline=get_lighter_color(body.color), start=0, extent=180, tags='object')
                self.widgets.canvas.create_arc(x-(radius-1), y-(radius-1), x + (radius-1), y + (radius-1), fill=body.color, outline=body.color, start=0, extent=180, tags='object')
            text_id = self.place_body_names(x, y, radius, body.name)
            self.body_ids.append((body.name, body_id, text_id))
        self.bring_hud_to_foreground()

    def bring_hud_to_foreground(self):
        for object in self.hud_objects:
            self.widgets.canvas.lift(object)

    def clear_canvas_bodies(self):
        for tag in ('object', 'object_text', 'planet_rings', 'orbit'):
            objects = self.widgets.canvas.find_withtag(tag)
            for obj in objects:
                self.widgets.canvas.delete(obj)

    def transform_coordinates_to_pixels(self, x, y):
        x_p = round(x * self.distance_scale + self.center_point_x)
        y_p = round(y * self.distance_scale + self.center_point_y)
        return x_p, y_p

    def text_object_size(self, text, font, font_size):
        font = tkfont.Font(family=font, size=font_size)
        text_width = font.measure(text)
        text_height = font.metrics("linespace")
        return text_width, text_height

    def place_body_names(self, center_x, center_y, radius, name):
        x, y, anchor = self.find_name_text_position(name, center_x, center_y, radius)
        text_id = self.widgets.canvas.create_text(x, y, anchor=anchor, text=name, fill=BODY_NAME_COLOR, font=(DEFAULT_FONT, TEXT_SIZE_NAME), tags='object_text')
        return text_id

    def find_name_text_position(self, name, center_x, center_y, planet_radius, padding=DEFAULT_NAME_TEXT_PADDING):
        text_width, text_height = self.text_object_size(name, DEFAULT_FONT, TEXT_SIZE_NAME)
        default_position = (center_x + planet_radius + padding, center_y, "w")  # Right
        positions = [default_position,
                     (center_x - planet_radius - padding, center_y, "e"),  # Left
                     (center_x, center_y - planet_radius - padding, "s"),  # Top
                     (center_x, center_y + planet_radius + padding, "n"),  # Bottom
                     (center_x - planet_radius - padding, center_y - planet_radius - padding, "se"),  # Top-left
                     (center_x - planet_radius - padding, center_y + planet_radius + padding, "ne"),  # Bottom-left
                     (center_x + planet_radius + padding, center_y - planet_radius - padding, "sw"),  # Top-right
                     (center_x + planet_radius + padding, center_y + planet_radius + padding, "nw")   # Bottom-right
                     ]
        least_overlap = -1
        least_overlap_position = default_position
        for position in positions:
            overlap = self.collision_with_other_body_names(text_width, text_height, position)
            if overlap > 0:
                if least_overlap > -1:
                    if least_overlap > overlap:
                        least_overlap_position = position
                        least_overlap = overlap
                else:
                    least_overlap = overlap
                    least_overlap_position = position
            else:
                if self.text_is_within_canvas(text_width, text_height, position):
                    return position
        return least_overlap_position

    def collision_with_other_body_names(self, width, height, position):
        x_new, y_new, a = position
        if a=="w":      x = x_new;                  y = y_new - round(height/2)
        elif a=="e":    x = x_new - width;          y = y_new - round(height/2)
        elif a=="s":    x = x_new - round(width/2); y = y_new - height
        elif a=="n":    x = x_new - round(width/2); y = y_new
        elif a=="se":   x = x_new - width;          y = y_new - height
        elif a=="ne":   x = x_new - width;          y = y_new
        elif a=="sw":   x = x_new;                  y = y_new - height
        elif a=="nw":   x = x_new;                  y = y_new
        max_overlap = 0
        for body_name, body_id, text_id in self.body_ids:
            text_bbox = self.widgets.canvas.bbox(text_id)
            body_bbox = self.widgets.canvas.bbox(body_id)
            if text_bbox == None or body_bbox == None:
                return 0
            overlap = max(self.overlap_with_bbox(x, y, width, height, text_bbox), self.overlap_with_bbox(x, y, width, height, body_bbox))
            if overlap > max_overlap:
                max_overlap = overlap
        return max_overlap

    def overlap_with_bbox(self, x1, y1, width, height, other_bbox):
        x2, y2, x2w, y2h = other_bbox
        Cx1 = x1 <= x2 <= x1 + width
        Cx2 = x2 <= x1 <= x2w
        Cy1 = y1 <= y2 <= y1 + height
        Cy2 = y2 <= y1 <= y2h
        if Cx1 and Cy1:
            return min((x2 - (x1+width)), x2w-x2, width) * min((y2 - (y1 + height)), y2h, height)
        elif Cx1 and Cy2:
            return min((x2 - (x1+width)), x2w-x2, width) * min((y1 - y2h), y2h, height)
        elif Cx2 and Cy1:
            return min((x1 - x2w), x2w-x2, width) * min((y2 - (y1 + height)), y2h, height)
        elif Cx2 and Cy2:
            return min((x1 - x2w), x2w-x2, width) * min((y1 - y2h), y2h, height)
        else:
            return 0

    def text_is_within_canvas(self, width, height, position):
        x, y, anchor = position
        if "w" in anchor:    # To the right of the position
            if not (x+width<=self.widgets.canvas.winfo_width() and round(y-height/2) >=0 and round(y+height/2) <= self.widgets.canvas.winfo_height()):
                return False
        if "e" in anchor:    # To the left of the position
            if not (x-width>=0 and round(y-height/2) >=0 and round(y+height/2) <= self.widgets.canvas.winfo_height()):
                return False
        if "s" in anchor:    # On top the position
            if not (y-height>=0 and round(x-width/2) >=0 and round(x+width/2) <= self.widgets.canvas.winfo_width()):
                return False
        if "n" in anchor:    # Below the position
            if not (y+height<=self.widgets.canvas.winfo_height() and round(x-width/2) >=0 and round(x+width/2) <= self.widgets.canvas.winfo_width()):
                return False
        return True

    def draw_planetary_rings(self, x, y, planet_radius, ring_value):
        ring_size = planet_radius * 1.5
        ring_thickness = max(round(planet_radius/30*ring_value), 1)
        if ring_value == 3:
            ring_thickness *= 2
            #ring_colors = ['white', 'lightgray', 'darkgray', 'gray']
            ring_colors = ['#1a1917', '#5c5344', '#232220', '#4e473f']
            for i, color in enumerate(ring_colors):
                self.draw_one_ring(x, y, planet_radius, ring_size+i*ring_thickness, color, ring_thickness)
        else:
            self.draw_one_ring(x, y, planet_radius, ring_size, "lightgray", ring_thickness)

    def draw_one_ring(self, x, y, planet_radius, ring_size, ring_color, ring_thickness):
        self.widgets.canvas.create_oval(x - ring_size,
                                        y - round(planet_radius/2),
                                        x + ring_size,
                                        y + round(planet_radius/2),
                                        outline=ring_color,
                                        width=ring_thickness,
                                        tags='planet_rings')

    def update_following_object(self, object_name="Sun"):
        self.following = self.celestial_bodies[object_name]
        self.origin = self.position_following()
        following_text = f"Following: {self.following.name.upper()}"
        properties_to_exclude = ["name", "x", "y", "z", "location_path", "texture", "rings", "surface",
                                 "atmosphere", "orbit_points", "orbit_resolution", "num_orbit_steps"]
        properties_to_format = ["luminosity", "radius", "mass", "temperature", "rotation_velocity",
                                "color_index", "average_orbital_speed", "orbital_period"]
        properties_to_round = ["rotation_period", "circumference"]
        property_lines = []
        for property_name, property_value in vars(self.following).items():
            if not (property_name in properties_to_exclude):
                property_print_name, units = property_name_and_units(property_name)
                if property_name in properties_to_round:
                    property_value = format_with_thousands_separator(property_value, 0)
                if property_name in properties_to_format:
                    property_value = format_with_thousands_separator(property_value)
                line = f"    - {property_print_name}: {property_value} {units}"
                property_lines.append(line)
        object_properties_text = "Information:\n" + "\n".join(property_lines)
        self.widgets.canvas.itemconfigure(self.following_object, text=following_text)
        self.widgets.canvas.itemconfigure(self.following_object_info, text=object_properties_text)

    def on_canvas_resize(self, event):
        new_width = event.width
        new_height = event.height
        self.widgets.canvas.configure(width=new_width, height=new_height)
        self.center_point_x, self.center_point_y = round(new_width/2), round(new_height/2)
        self.update_standard_draw_scale(new_width, new_height)
        self.update_distance_scale()
        self.draw_celestial_bodies()

    def modify_zoom_level(self, event):
        if event.state & 0x1:  # Check if Shift key is pressed
            if event.delta > 0:
                scale_factor = 0.1  # Increase scale by 0.1 for fine-grained zoom in
            else:
                scale_factor = -0.1  # Decrease scale by 0.1 for fine-grained zoom out
        elif event.state & 0x4: # Check if Ctrl key is pressed
            if event.delta > 0:
                scale_factor = self.modified_scale  # Increase scale by 0.1 for fine-grained zoom in
            else:
                scale_factor = -self.modified_scale/2  # Decrease scale by 0.1 for fine-grained zoom out
        else:
            if event.delta > 0:
                scale_factor = 1.0  # Increase scale by 1 for regular zoom in
            else:
                scale_factor = -1.0  # Decrease scale by 1 for regular zoom out
        self.modified_scale = round(self.modified_scale + scale_factor, 1)
        if self.modified_scale < 0.1:
            self.modified_scale = 0.1
        self.update_distance_scale()
        self.draw_celestial_bodies()

    def update_distance_scale(self):
        self.distance_scale = self.standard_draw_scale * self.modified_scale
        self.update_scale_text()

    def handle_canvas_double_click(self, event):
        clicked_body_ids = self.widgets.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for object_name, body_id, text_id in self.body_ids:
            if body_id in clicked_body_ids or text_id in clicked_body_ids:
                self.update_following_object(object_name)
                #self.update_all_bodies_positions()
                self.update_standard_draw_scale(self.widgets.canvas.winfo_width(), self.widgets.canvas.winfo_height())
                self.draw_celestial_bodies()
                break

    def mouse_hover(self, event):
        x = (event.x - self.center_point_x) / self.distance_scale
        y = (event.y - self.center_point_y) / self.distance_scale
        distance = sqrt(x**2 + y**2)
        self.widgets.canvas.delete("cursor_distance_text")
        cursor_position_text_km = f"Position: x = {format_with_thousands_separator(x, 0)} | y = {format_with_thousands_separator(y, 0)} | Distance = {format_with_thousands_separator(distance, 0)} (km)"
        cursor_position_text_au = f"Position: x = {format_with_thousands_separator(x/AU, 4)} | y = {format_with_thousands_separator(y/AU, 4)} | Distance = {format_with_thousands_separator(distance/AU, 4)} (AU)"
        self.widgets.canvas.itemconfigure(self.distance_text_km, text=cursor_position_text_km)
        self.widgets.canvas.itemconfigure(self.distance_text_au, text=cursor_position_text_au)

    def handle_time_adjustment(self, event):
        fine_adjustment = event.state & 0x1     # Check if the Shift key is pressed
        coarse_adjustment = event.state & 0x4   # Check if the Ctrl key is pressed
        if event.keysym == "Left":
            if fine_adjustment:
                self.timestamp_days -= 1
            elif coarse_adjustment:
                self.timestamp_years -= 1
            else:
                self.timestamp_months -= 1
        elif event.keysym == "Right":
            if fine_adjustment:
                self.timestamp_days += 1
            elif coarse_adjustment:
                self.timestamp_years += 1
            else:
                self.timestamp_months += 1
        self.timestamp = self.convert_to_julian_date()
        self.update_time_text()
        last_positions = self.save_positions()
        self.update_all_bodies_positions()
        position_changes = self.calculate_change_vectors(last_positions)
        self.update_orbits(position_changes)
        self.draw_celestial_bodies()

    def save_positions(self):
        positions = {}
        for body_name, body_obj in self.celestial_bodies.items():
            positions[body_name] = {"x": body_obj.x,
                                    "y": body_obj.y,
                                    "z": body_obj.z}
        return positions

    def calculate_change_vectors(self, last_positions):
        change_vectors = {}
        for body_name, body_obj in self.celestial_bodies.items():
            change_vectors[body_name] = {"x": body_obj.x - last_positions[body_name]["x"],
                                         "y": body_obj.y - last_positions[body_name]["y"],
                                         "z": body_obj.z - last_positions[body_name]["z"]}
        return change_vectors

    def update_time_text(self):
        time_text = f"Current date: {self.date} - adjustment {self.timestamp_days} days, {self.timestamp_months} months, {self.timestamp_years} years"
        self.widgets.canvas.itemconfigure(self.time_text, text=time_text)

    def update_scale_text(self):
        scale_text = f"Scale: {self.modified_scale}"
        self.widgets.canvas.itemconfigure(self.scale_text, text=scale_text)

    def body_position(self, body_location_path, timestamp=None):
        position = [0, 0, 0]
        if timestamp==None:
            timestamp = self.timestamp
        for index in range(len(body_location_path) - 1):
            index1 = body_location_path[index]
            index2 = body_location_path[index + 1]
            step = self.kernel[index1, index2].compute(timestamp)
            position += step
        return position

    def print_all_bodies_positions(self):
        for body_name, body_obj in self.celestial_bodies.items():
            print(f"{body_name}: ({body_obj.x}, {body_obj.y}, {body_obj.z})")

    def position_following(self):
        position = self.body_position(self.following.location_path)
        origin = classes.Point(position[0], position[1], position[2])
        return origin

    def load_orbits(self, resolution=ORBIT_RESOLUTION):
        for body_name, body_obj in self.celestial_bodies.items():
            body_obj.orbit_points = []
            period = body_obj.orbital_period
            if period > 0:
                time_step = period/resolution*JULIAN_DATE_DAY
                num_steps = round(period/time_step)
                parent_body = self.celestial_bodies.get(body_obj.parent_body)
                for i in range(num_steps+1):
                    date = MIN_JULIAN_DATE + i * time_step
                    if date <= MAX_JULIAN_DATE:
                        position = self.body_position(body_obj.location_path, date) - self.body_position(parent_body.location_path, date) + self.body_position(parent_body.location_path)
                        if not DRAW_3D:
                            body_obj.orbit_points.append((position[0], position[1]))
                        else:
                            body_obj.orbit_points.append((position[0], position[1], position[2]))

    def update_orbits(self, change_vectors):
        for body_name, body_obj in self.celestial_bodies.items():
            if body_obj.parent_body in change_vectors and not body_obj=="Sun":
                change_vector = change_vectors[body_obj.parent_body]
                for i in range(len(body_obj.orbit_points)):
                    body_obj.orbit_points[i] = (body_obj.orbit_points[i][0] + change_vector["x"],
                                                body_obj.orbit_points[i][1] + change_vector["y"],
                                                body_obj.orbit_points[i][2] + change_vector["z"] if DRAW_3D else 0)

    def draw_orbits(self):
        for body_name, body in self.celestial_bodies.items():
            for i in range(len(body.orbit_points)-1):
                x1, y1 = body.orbit_points[i][0]-self.origin.x, body.orbit_points[i][1]-self.origin.y
                x2, y2 = body.orbit_points[i+1][0]-self.origin.x, body.orbit_points[i+1][1]-self.origin.y
                if DRAW_3D:
                    z1 = body.orbit_points[i][2]-self.origin.z
                    z2 = body.orbit_points[i+1][2]-self.origin.z
                    (x1, y1, z1) = (x1, y1, z1) @ self.rotation_matrix
                    (x2, y2, z2) = (x2, y2, z2) @ self.rotation_matrix
                x1, y1 = self.transform_coordinates_to_pixels(x1, y1)
                x2, y2 = self.transform_coordinates_to_pixels(x2, y2)
                self.widgets.canvas.create_line(x1, y1, x2, y2, fill=ORBIT_FILL_COLOR, dash=(2, 2), tags='orbit')

    def update_all_bodies_positions(self):
        self.origin = self.position_following()
        for body_name, body_obj in self.celestial_bodies.items():
            position = self.body_position(body_obj.location_path)
            self.celestial_bodies[body_name].x = position[0]
            self.celestial_bodies[body_name].y = position[1]
            self.celestial_bodies[body_name].z = position[2]

    def update_boundaries(self):
        max_x = max(abs(body.x-self.origin.x) for body in self.celestial_bodies.values())
        max_y = max(abs(body.y-self.origin.y) for body in self.celestial_bodies.values())
        self.max_distance_width = max_x #- min_x
        self.max_distance_height = max_y #- min_y
        if DRAW_3D:
            min_z = min(body.z for body in self.celestial_bodies.values())
            max_z = max(body.z for body in self.celestial_bodies.values())
            self.max_distance_depth = max_z - min_z

    def convert_to_julian_date(self, date=None, d=None, m=None, y=None):
        if date is None:
            dt = self.date
        else:
            dt = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        year = dt.year + self.timestamp_years
        month = dt.month + self.timestamp_months
        day = dt.day + self.timestamp_days
        hour= dt.hour
        minute = dt.minute
        second = dt.second
        if not d is None:
            day += d
        if not m is None:
            month += m
        if not y is None:
            year += y
        julian_date = 367 * year - (7 * (year + ((month + 9) // 12))) // 4 + (275 * month) // 9 + day + 1721013.5
        julian_date += (hour + (minute / 60) + (second / 3600)) / 24
        if julian_date < MIN_JULIAN_DATE:
            julian_date = MIN_JULIAN_DATE
        elif julian_date > MAX_JULIAN_DATE:
            julian_date = MAX_JULIAN_DATE
        return julian_date

class Widgets(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(master=parent)
        self.configure(fg_color=DEFAULT_BACKGROUND)
        self.canvas = ctk.CTkCanvas(parent, bg="black", width=WINDOW_SIZE[0], height=WINDOW_SIZE[1])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.update_idletasks()

if __name__ == "__main__":
    root = App()
    root.mainloop()
    root.close_ephemeris_data()
    root.destroy