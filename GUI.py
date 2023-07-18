from settings import *
import customtkinter as ctk
import classes
import datetime
from functions import format_with_thousands_separator, property_name_and_units
from math import sqrt
from numpy import array, eye, sin, cos
from creators import create_bodies, create_test_spaceship
from ephemeris_data import check_ephemeris_file_update, load_ephemeris_data, close_ephemeris_data
from creators import *
from graphics import draw_celestial_bodies, update_standard_draw_scale, update_distance_scale
from orbital_functions import simulate_spaceship_trajectory

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.widgets = self.configure_app_window()
        self.configure_canvas_hud()
        self.bind_events()
        check_ephemeris_file_update(self)
        load_ephemeris_data(self)

        self.celestial_bodies = create_bodies(star_data=Star_data,
                                              planet_data=Planet_data,
                                              moon_data=None)

        self.date = datetime.datetime.now()
        self.timestamp = self.convert_to_julian_date()
        self.simulation_step_index = 0
        self.update_time_text()

        self.update_following_object()
        self.load_orbits()

        self.iterations = 100
        self.current_iteration = 0
        self.spaceship = create_test_spaceship()
        test_input_vector = []
        for i in range(self.iterations):
            test_input_vector.append((0, 1, 0, 0, 1))
        simulate_spaceship_trajectory(self, self.date, test_input_vector)
        self.spaceship.x = 0
        self.spaceship.y = 0
        self.spaceship.z = 0
        self.update_all_bodies_positions()
        self.update_boundaries()

        self.modified_scale = 1.0
        self.center_point_x, self.center_point_y = round(self.widgets.canvas.winfo_reqwidth()/2), round(self.widgets.canvas.winfo_reqheight()/2)
        update_standard_draw_scale(self, self.widgets.canvas.winfo_reqwidth(), self.widgets.canvas.winfo_reqheight())
        update_distance_scale(self)
        self.rotation_matrix = eye(3)
        self.pitch_angle = 0
        self.roll_angle = 0
        self.yaw_angle = 0
        draw_celestial_bodies(self)
        self.auto_play = False
        self.update_auto_play_text()

    def configure_app_window(self):
        self.title("SOLARA: Solar System Simulator")
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.resizable=(True, True)
        self.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])
        self.iconbitmap("logos/logo-2.ico")
        self.configure(fg_color = DEFAULT_BACKGROUND)
        widgets = Widgets(self)
        return widgets

    def configure_canvas_hud(self):
        self.time_text = self.widgets.canvas.create_text(10, 10, anchor="nw", fill=DEFAULT_FONT_COLOR, font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.auto_play_text = self.widgets.canvas.create_text(10, 10+INFO_TEXT_SEPARATION, anchor="nw", fill=SCALE_TEXT_COLOR, text="Auto run: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.scale_text = self.widgets.canvas.create_text(10, 10+2*INFO_TEXT_SEPARATION, anchor="nw", fill=SCALE_TEXT_COLOR, text="Scale", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.distance_text_km = self.widgets.canvas.create_text(10, 10+3*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Distance km", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.distance_text_au = self.widgets.canvas.create_text(10, 10+4*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Distance AU", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.following_object = self.widgets.canvas.create_text(10, 10+5*INFO_TEXT_SEPARATION, anchor="nw", fill=FOLLOWING_OBJECT_TEXT_COLOR, text="Following: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.following_object_info = self.widgets.canvas.create_text(10, 10+6*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Object info: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.hud_objects = (self.time_text, self.auto_play_text, self.scale_text, self.distance_text_km,
                            self.distance_text_au, self.following_object, self.following_object_info)

    def bind_events(self):
        self.widgets.canvas.bind("<Configure>", self.on_canvas_resize)
        self.widgets.canvas.bind("<MouseWheel>", self.modify_zoom_level)
        self.widgets.canvas.bind("<Motion>", self.mouse_hover)
        self.widgets.canvas.bind("<Double-Button-1>", self.handle_canvas_double_click)
        self.widgets.canvas.bind("<ButtonPress-1>", self.start_mouse_drag)
        self.widgets.canvas.bind("<ButtonPress-3>", self.start_mouse_drag)
        self.widgets.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.widgets.canvas.bind("<B3-Motion>", self.on_mouse_drag)
        self.widgets.canvas.bind("<ButtonRelease-1>", self.release_mouse_drag)
        self.widgets.canvas.bind("<ButtonRelease-3>", self.release_mouse_drag)
        self.bind("<Escape>", self.reset_view)
        self.bind("<Left>", self.handle_time_adjustment)
        self.bind("<Right>", self.handle_time_adjustment)
        self.bind("<Up>", self.change_time_step)
        self.bind("<Down>", self.change_time_step)
        self.bind("<space>", self.pause_resume_simulation)

    def start_mouse_drag(self, event):
        self.mouse_drag_starting_point = (event.x, event.y)

    def on_mouse_drag(self, event):
        if self.mouse_drag_starting_point is None:
            return
        delta_x = event.x - self.mouse_drag_starting_point[0]
        delta_y = event.y - self.mouse_drag_starting_point[1]
        if event.state == 264:
            self.yaw_angle += delta_x * ROTATION_SENSITIVITY
            self.roll_angle += delta_y * ROTATION_SENSITIVITY
        elif event.state == 1032:
            self.pitch_angle += -delta_x * ROTATION_SENSITIVITY
        rotation_matrix_yaw = array([[cos(self.yaw_angle), -sin(self.yaw_angle), 0],
                                     [sin(self.yaw_angle), cos(self.yaw_angle), 0],
                                     [0, 0, 1]])
        rotation_matrix_pitch = array([[cos(self.pitch_angle), 0, sin(self.pitch_angle)],
                                       [0, 1, 0],
                                       [-sin(self.pitch_angle), 0, cos(self.pitch_angle)]])
        rotation_matrix_roll = array([[1, 0, 0],
                                     [0, cos(self.roll_angle), -sin(self.roll_angle)],
                                     [0, sin(self.roll_angle), cos(self.roll_angle)]])
        self.rotation_matrix = rotation_matrix_yaw @ rotation_matrix_pitch @ rotation_matrix_roll
        self.mouse_drag_starting_point = (event.x, event.y)
        draw_celestial_bodies(self)

    def release_mouse_drag(self, event):
        self.mouse_drag_starting_point = None

    def reset_view(self, event):
        self.rotation_matrix = eye(3)
        self.modified_scale = 1.0
        self.yaw_angle = 0
        self.roll_angle = 0
        self.pitch_angle = 0
        update_distance_scale(self)
        draw_celestial_bodies(self)

    def pause_resume_simulation(self, event):
        if self.auto_play:
            self.auto_play = False
            for id in self.after_ids:
                self.after_cancel(id)
        else:
            self.after_ids = []
            self.auto_play = True
            after_id = self.after(MILISECONDS_PER_FRAME, self.advance_step)
            self.after_ids.append(after_id)
        self.update_auto_play_text()

    def advance_step(self):
        if self.auto_play:
            self.handle_time_adjustment(auto_play=True)
            self.after(MILISECONDS_PER_FRAME, self.advance_step)

    def update_following_object(self, object_name="Sun"):
        if object_name!="Spaceship":
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
        else:
            self.following = self.spaceship
            self.origin = classes.Point(self.spaceship.x, self.spaceship.y, self.spaceship.z)
            following_text = "Following: SPACESHIP"
            object_properties_text = "Test spaceship"
        self.widgets.canvas.itemconfigure(self.following_object, text=following_text)
        self.widgets.canvas.itemconfigure(self.following_object_info, text=object_properties_text)

    def on_canvas_resize(self, event):
        new_width = event.width
        new_height = event.height
        self.widgets.canvas.configure(width=new_width, height=new_height)
        self.center_point_x, self.center_point_y = round(new_width/2), round(new_height/2)
        update_standard_draw_scale(self, new_width, new_height)
        update_distance_scale(self)
        draw_celestial_bodies(self)

    def handle_canvas_double_click(self, event):
        clicked_body_ids = self.widgets.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for object_name, body_id, text_id in self.body_ids:
            if body_id in clicked_body_ids or text_id in clicked_body_ids:
                self.update_following_object(object_name)
                update_standard_draw_scale(self, self.widgets.canvas.winfo_width(), self.widgets.canvas.winfo_height())
                draw_celestial_bodies(self)
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

    def handle_time_adjustment(self, event=None, auto_play=False):
        number = list(simulation_steps.items())[self.simulation_step_index][1]
        if self.simulation_step_index <= 1:
            time_step = datetime.timedelta(seconds=number)
        elif self.simulation_step_index <= 4:
            time_step = datetime.timedelta(minutes=number)
        elif self.simulation_step_index <= 6:
            time_step = datetime.timedelta(hours=number)
        else:
            time_step = datetime.timedelta(days=number)
        if auto_play or event.keysym == "Right":
            self.date += time_step
            if self.current_iteration < self.iterations:
                self.current_iteration += 1
        elif event.keysym == "Left":
            self.date -= time_step
            if self.current_iteration > 0:
                self.current_iteration -= 1
        self.timestamp = self.convert_to_julian_date()
        self.update_time_text()
        last_positions = self.save_positions()
        self.update_all_bodies_positions()
        position_changes = self.calculate_change_vectors(last_positions)
        self.update_orbits(position_changes)
        if self.spaceship!=None:
            if self.following == self.spaceship:
                self.origin = self.position_following(True)
        draw_celestial_bodies(self)

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
        update_distance_scale(self)
        draw_celestial_bodies(self)

    def change_time_step(self, event):
        if event.keysym=="Up":
            if self.simulation_step_index < len(simulation_steps)-1:
                self.simulation_step_index += 1
        elif event.keysym=="Down":
            if self.simulation_step_index > 0:
                self.simulation_step_index -= 1
        self.update_time_text()

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

    def update_auto_play_text(self):
        auto_play_text = f"Auto run: {'Running' if self.auto_play else 'Stopped'}"
        self.widgets.canvas.itemconfigure(self.auto_play_text, text=auto_play_text, fill=AUTO_RUN_TEXT_COLOR_RUN if self.auto_play else AUTO_RUN_TEXT_COLOR_STOP)

    def update_time_text(self):
        time_step_name = list(simulation_steps.items())[self.simulation_step_index][0]
        show_date = self.date.strftime('%Y-%m-%d %H:%M:%S')
        time_text = f"Current date: {show_date} - Time step = {time_step_name}"
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

    def position_following(self, spaceship=False):
        if not spaceship:
            position = self.body_position(self.following.location_path)
        else:
            position = self.spaceship.x, self.spaceship.y, self.spaceship.z
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

    def update_all_bodies_positions(self):
        self.origin = self.position_following(self.following==self.spaceship)
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

    def convert_to_julian_date(self, date=None, seconds=None, minutes=None,
                                hours=None, days=None, months=None, years=None):
        if date is None:
            if self.date is None:
                self.date = datetime.datetime.now()
            date = self.date
        year = date.year
        month = date.month
        day = date.day
        hour= date.hour
        minute = date.minute
        second = date.second
        if seconds is not None: second += seconds
        if minutes is not None: minute += minutes
        if hours is not None: hour += hours
        if days is not None: day += days
        if months is not None: month += months
        if years is not None: year += years
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
    close_ephemeris_data(root)
    root.destroy