from settings import *
import customtkinter as ctk
import tkinter.font as tkfont
import requests
import os
import email.utils
import classes
from jplephem.spk import SPK
import datetime
from functions import get_lighter_color, format_with_thousands_separator, property_name_and_units, calculate_orbit_parameters
from math import sqrt

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.widgets = self.configure_app_window()
        self.configure_canvas_info_objects()
        self.bind_events()
        self.check_ephemeris_file_update()
        self.load_ephemeris_data()

        self.celestial_bodies = self.create_bodies()
        self.update_following_object()
        
        self.date = datetime.datetime.now()
        self.timestamp_months = 0
        self.timestamp_years = 0
        self.timestamp = self.convert_to_julian_date()
        self.update_time_text()

        self.load_orbits()
        self.update_all_bodies_positions()
        self.update_boundaries()

        self.modified_scale = 1.0
        self.center_point_x, self.center_point_y = round(self.widgets.canvas.winfo_reqwidth()/2), round(self.widgets.canvas.winfo_reqheight()/2)
        self.update_standard_draw_scale(self.widgets.canvas.winfo_reqwidth(), self.widgets.canvas.winfo_reqheight())
        self.update_distance_scale()
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

    def configure_canvas_info_objects(self):
        self.time_text = self.widgets.canvas.create_text(10, 10, anchor="nw", fill="white", font=("Arial", TEXT_SIZE_INFO), tags="info")
        self.scale_text = self.widgets.canvas.create_text(10, 10+INFO_TEXT_SEPARATION, anchor="nw", fill="white", text="Scale", font=("Arial", TEXT_SIZE_INFO), tags="info")
        self.distance_text_km = self.widgets.canvas.create_text(10, 10+2*INFO_TEXT_SEPARATION, anchor="nw", fill="white", text="Distance km", font=("Arial", TEXT_SIZE_INFO), tags="info")
        self.distance_text_au = self.widgets.canvas.create_text(10, 10+3*INFO_TEXT_SEPARATION, anchor="nw", fill="white", text="Distance AU", font=("Arial", TEXT_SIZE_INFO), tags="info")
        self.following_object = self.widgets.canvas.create_text(10, 10+4*INFO_TEXT_SEPARATION, anchor="nw", fill="white", text="Following: ", font=("Arial", TEXT_SIZE_INFO), tags="info")
        self.following_object_info = self.widgets.canvas.create_text(10, 10+5*INFO_TEXT_SEPARATION, anchor="nw", fill="white", text="Object info: ", font=("Arial", TEXT_SIZE_INFO), tags="info")

    def bind_events(self):
        self.widgets.canvas.bind("<Configure>", self.on_canvas_resize)
        self.widgets.canvas.bind("<MouseWheel>", self.modify_zoom_level)
        self.widgets.canvas.bind("<Motion>", self.mouse_hover)
        self.widgets.canvas.bind("<Double-Button-1>", self.handle_canvas_double_click)
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
            for star_name, star_properties in Star_data.items():
                star = classes.Star(star_name, **star_properties)
                celestial_bodies[star_name] = star
        if planets:
            for planet_name, planet_properties in Planet_data.items():
                planet = classes.Planet(planet_name, **planet_properties)
                celestial_bodies[planet_name] = planet
        if moons:
            for moon_name, moon_properties in Moon_data.items():
                moon = classes.Planet(moon_name, **moon_properties)
                celestial_bodies[moon_name] = moon
        return celestial_bodies

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
            x, y, z = self.transform_coordinates_to_pixels(body.x, body.y, body.z)
            radius = round(body.radius * self.distance_scale)
            radius = max(radius, 1)
            if not DRAW_3D:
                body_id = self.widgets.canvas.create_oval(x-radius, y-radius, x + radius, y + radius, fill=body.color, outline=get_lighter_color(body.color), tags='object')
                if radius > 3 and body.rings > 0:
                    self.draw_planetary_rings(x, y, radius, body.rings)
                    self.widgets.canvas.create_arc(x-radius, y-radius, x + radius, y + radius, fill=body.color, outline=get_lighter_color(body.color), start=0, extent=180, tags='object')
                    self.widgets.canvas.create_arc(x-(radius-1), y-(radius-1), x + (radius-1), y + (radius-1), fill=body.color, outline=body.color, start=0, extent=180, tags='object')
                text_id = self.place_body_names(x, y, radius, body.name)
                self.body_ids.append((body.name, body_id, text_id))
            else:
                # TO DO: draw celestial bodies in 3D representation
                pass

    def clear_canvas_bodies(self):
        for tag in ('object', 'object_text', 'planet_rings', 'orbit'):
            objects = self.widgets.canvas.find_withtag(tag)
            for obj in objects:
                self.widgets.canvas.delete(obj)

    def transform_coordinates_to_pixels(self, x, y, z):
        x_p = round(x * self.distance_scale + self.center_point_x)
        y_p = round(y * self.distance_scale + self.center_point_y)
        if not DRAW_3D:
            z_p = 0
        else:
            #z_p = round(z * self.distance_scale + center_point_y)
            pass
        return x_p, y_p, z_p

    def get_text_size(self, text, font_size):
        font = tkfont.Font(family="Arial", size=font_size)
        text_width = font.measure(text)
        text_height = font.metrics("linespace")
        return text_width, text_height

    def place_body_names(self, x, y, radius, name):
        # To DO
        coso = self.get_text_size(name, TEXT_SIZE_NAME)
        text_id = self.widgets.canvas.create_text(x + radius + 10, y, anchor='w', text=name, fill=BODY_NAME_COLOR, font=("Arial", TEXT_SIZE_NAME), tags='object_text')
        return text_id

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
        following_text = f"Following: {self.following.name}"
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
        self.distance_scale = SCALE_MODIFIER * self.standard_draw_scale * self.modified_scale
        self.update_scale_text()

    def handle_canvas_double_click(self, event):
        clicked_body_ids = self.widgets.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for object_name, body_id, text_id in self.body_ids:
            if body_id in clicked_body_ids or text_id in clicked_body_ids:
                self.update_following_object(object_name)
                self.update_all_bodies_positions()
                self.update_standard_draw_scale(self.widgets.canvas.winfo_reqwidth(), self.widgets.canvas.winfo_reqheight())
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
        if event.keysym == "Left":
            if fine_adjustment:
                self.timestamp_months -= 1
            else:
                self.timestamp_years -= 1
        elif event.keysym == "Right":
            if fine_adjustment:
                self.timestamp_months += 1
            else:
                self.timestamp_years += 1
        self.timestamp = self.convert_to_julian_date()
        self.update_time_text()
        self.update_all_bodies_positions()
        self.draw_celestial_bodies()

    def update_time_text(self):
        time_text = f"Current date: {self.date} - adjustment {self.timestamp_months} months, {self.timestamp_years} years"
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

    def load_orbits(self, increment=JULIAN_DATE_MONTH):
        for body_name, body_obj in self.celestial_bodies.items():
            step_size, num_steps = calculate_orbit_parameters(body_name)
            for i in range(num_steps):
                date = int(MIN_JULIAN_DATE+0.5 + (i * step_size))
                position = self.body_position(body_obj.location_path, date)
                if not DRAW_3D:
                    body_obj.orbit_points.append((position[0], position[1]))
                else:
                    body_obj.orbit_points.append((position[0], position[1], position[2]))
            # date = MIN_JULIAN_DATE
            # while date <= MAX_JULIAN_DATE:
            #     position = self.body_position(body_obj, date)
            #     if not DRAW_3D:
            #         body_obj.orbit.append((position[0], position[1]))
            #     else:
            #         body_obj.orbit.append((position[0], position[1], position[2]))
            #     date += increment

    def draw_orbits(self):
        for body_name, body in self.celestial_bodies.items():
            for i in range(len(body.orbit_points)-1):
                if not DRAW_3D:
                    x1, y1, z1 = self.transform_coordinates_to_pixels(x=body.orbit_points[i][0]-self.origin.x, y=body.orbit_points[i][1]-self.origin.y, z=0)
                    x2, y2, z2 = self.transform_coordinates_to_pixels(x=body.orbit_points[i+1][0]-self.origin.x, y=body.orbit_points[i+1][1]-self.origin.y, z=0)
                    self.widgets.canvas.create_line(x1, y1, x2, y2, fill="white", dash=(1, 1), tags='orbit')
                else:
                    x1, y1, z1 = self.transform_coordinates_to_pixels(x=body.orbit_points[i][0], y=body.orbit_points[i][1], z=body.orbit_points[i][2])
                    x2, y2, z2 = self.transform_coordinates_to_pixels(x=body.orbit_points[i+1][0], y=body.orbit_points[i+1][1], z=body.orbit_points[i+1][2])

    def update_all_bodies_positions(self):
        self.origin = self.position_following()
        for body_name, body_obj in self.celestial_bodies.items():
            position = self.body_position(body_obj.location_path)
            self.celestial_bodies[body_name].x = position[0] - self.origin.x
            self.celestial_bodies[body_name].y = position[1] - self.origin.y
            self.celestial_bodies[body_name].z = position[2] - self.origin.z

    def update_boundaries(self):
        #min_x = min(abs(body.x-self.following.x) for body in self.celestial_bodies.values())
        max_x = max(abs(body.x-self.origin.x) for body in self.celestial_bodies.values())
        #min_y = min(body.y-self.following.y for body in self.celestial_bodies.values())
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
        day = dt.day
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