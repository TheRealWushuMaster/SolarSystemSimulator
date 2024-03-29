import customtkinter as ctk
import locale
from tkinter import Listbox as tkListBox
from settings import *
from classes import Simulation, Point, SpaceshipState, FlightPlan
from functions import format_with_thousands_separator, property_name_and_units, \
    calculate_additional_properties
from math import sqrt
from numpy import array, eye, sin, cos
from creators import create_bodies, create_test_spaceship, create_iss
from ephemeris_data import check_ephemeris_file_update, load_ephemeris_data, \
    close_ephemeris_data
from creators import create_bodies, create_test_spaceship
from graphics import draw_celestial_bodies, update_standard_draw_scale, \
    update_distance_scale


class SetupSimulationWindow(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        # Save original locale settings
        original_locale = locale.getlocale(locale.LC_NUMERIC)
        # Change locale settings so ctk will work
        locale.setlocale(locale.LC_NUMERIC, "C")
        
        self.geometry("400x300")
        self.configure(fg_color=DEFAULT_BACKGROUND)
        self.title("Simulation Setup")
        self.iconbitmap(default=WINDOW_LOGO)
        self.update_idletasks()
        
        # Create objectives dropdown menu
        objectives_label = ctk.CTkLabel(master=self, text="Select Objective:")
        objectives_label.pack(padx=DEFAULT_NAME_TEXT_PADDING, pady=DEFAULT_NAME_TEXT_PADDING)
        objectives_options = ["Fastest Time", "Least Fuel Usage", "Shortest Distance"]
        objectives_var = ctk.StringVar(master=self)
        objectives_var.set(objectives_options[0])
        # objectives_dropdown = ctk.CTkComboBox(master=self, textvariable=objectives_var, values=objectives_options)
        objectives_dropdown = ctk.CTkComboBox(master=self, values=objectives_options)
        objectives_dropdown.pack(padx=DEFAULT_NAME_TEXT_PADDING, pady=DEFAULT_NAME_TEXT_PADDING)

        # Add more widgets for spaceship setup, destination selection, etc.

        run_button = ctk.CTkButton(master=self, text="Run Simulation")
        run_button.pack(padx=DEFAULT_NAME_TEXT_PADDING, pady=DEFAULT_NAME_TEXT_PADDING)
        
        # self.mainloop()
        
        # Revert changes to the locale settings
        locale.setlocale(locale.LC_NUMERIC, original_locale)
        


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.widgets = self.configure_app_window()
        self.configure_canvas_hud()
        self.bind_events()
        check_ephemeris_file_update(self)
        load_ephemeris_data(self)

        calculate_additional_properties(Star_data, color=True)
        calculate_additional_properties(Planet_data)
        calculate_additional_properties(Moon_data)
        celestial_bodies = create_bodies(star_data=Star_data,
                                         planet_data=Planet_data,
                                         moon_data=Moon_data)
        self.simulation = Simulation(gui=self,
                                     start_time="now",
                                     end_time=None,
                                     celestial_bodies=celestial_bodies)

        self.update_all_bodies_positions()

        self.update_time_text()

        self.load_orbits()
        self.update_boundaries()

        flight_plan = FlightPlan()
        #flight_plan.add_delta_v(delta_v=0.8314, reference="Earth", duration=10)
        initial_state = self.return_orbit_body_state(body_name="Earth", altitude=1000)
        #initial_state.velocity_x += 0.8314
        #for i in range(5):
        #    flight_plan.add_coast(10)
        # for i in range(1):
        #     flight_plan.add_delta_v(2.3354*1.3, 10)
        # flight_plan.add_coast(10)
        spaceship = create_test_spaceship(initial_state=initial_state,
                                          flight_plan=flight_plan)
        self.simulation.add_spaceship(spaceship_name="Test Spaceship", spaceship=spaceship)

        initial_state = self.return_orbit_body_state(body_name="Moon", altitude=500)
        spaceship = create_test_spaceship(initial_state=initial_state)
        self.simulation.add_spaceship(spaceship_name="Another Test Spaceship", spaceship=spaceship)

        iss = create_iss(self.simulation)
        self.simulation.add_spaceship(spaceship_name="ISS", spaceship=iss)

        self.modified_scale = 1.0
        self.center_point_x, self.center_point_y = round(self.widgets.canvas.winfo_reqwidth()/2), round(self.widgets.canvas.winfo_reqheight()/2)
        update_standard_draw_scale(self, self.widgets.canvas.winfo_reqwidth(), self.widgets.canvas.winfo_reqheight())
        update_distance_scale(self)
        self.rotation_matrix = eye(3)
        self.pitch_angle = 0
        self.roll_angle = 0
        self.yaw_angle = 0
        draw_celestial_bodies(self)
        
        self.update_auto_play_text()

    def configure_app_window(self):
        self.title("SOLARA: Solar System Simulator")
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.resizable=(True, True)
        self.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])
        self.iconbitmap(default=WINDOW_LOGO)
        self.configure(fg_color = DEFAULT_BACKGROUND)
        widgets = Widgets(self)
        widgets.setup_simulation_button.configure(command=self.show_setup_window)
        self.setup_simulation_window = None
        return widgets

    def configure_canvas_hud(self):
        self.time_text = self.widgets.canvas.create_text(10, 10, anchor="nw", fill=DEFAULT_FONT_COLOR, font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.auto_play_text = self.widgets.canvas.create_text(10, 10+INFO_TEXT_SEPARATION, anchor="nw", fill=SCALE_TEXT_COLOR, text="Auto run: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.scale_text = self.widgets.canvas.create_text(10, 10+2*INFO_TEXT_SEPARATION, anchor="nw", fill=SCALE_TEXT_COLOR, text="Scale", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.distance_text_km = self.widgets.canvas.create_text(10, 10+3*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Distance km", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.distance_text_au = self.widgets.canvas.create_text(10, 10+4*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Distance AU", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.velocity_reference_text = self.widgets.canvas.create_text(10, 10+5*INFO_TEXT_SEPARATION, anchor="nw", fill=VELOCITY_REFERENCE_TEXT_COLOR, text="Velocity reference: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.following_object = self.widgets.canvas.create_text(10, 10+6*INFO_TEXT_SEPARATION, anchor="nw", fill=FOLLOWING_OBJECT_TEXT_COLOR, text="Following: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO, "bold"), tags="info")
        self.following_object_info = self.widgets.canvas.create_text(10, 10+7*INFO_TEXT_SEPARATION, anchor="nw", fill=DEFAULT_FONT_COLOR, text="Object info: ", font=(DEFAULT_FONT, TEXT_SIZE_INFO), tags="info")
        self.hud_objects = (self.time_text, self.auto_play_text, self.scale_text,
                            self.distance_text_km, self.distance_text_au, self.following_object,
                            self.velocity_reference_text, self.following_object_info)

    def bind_events(self):
        self.widgets.canvas.bind("<Configure>", self.on_canvas_resize)
        self.widgets.canvas.bind("<MouseWheel>", self.modify_zoom_level)
        self.widgets.canvas.bind("<Motion>", self.mouse_hover)
        self.widgets.canvas.bind("<Double-Button-1>", self.handle_canvas_double_click)
        self.widgets.canvas.bind("<ButtonPress-1>", self.start_mouse_drag)
        self.widgets.canvas.bind("<ButtonPress-2>", self.change_velocity_reference)
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

    def show_setup_window(self):
        if (self.setup_simulation_window is None
                or not self.setup_simulation_window.winfo_exists()):
            self.setup_simulation_window = SetupSimulationWindow()
        self.setup_simulation_window.focus()

    def change_velocity_reference(self, event):
        clicked_body_ids = self.widgets.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for object_name, body_id, text_id in self.body_ids:
            if body_id in clicked_body_ids or text_id in clicked_body_ids:
                self.simulation.velocity_reference_object = object_name
                self.simulation.update_velocity_reference()
                break

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
        if self.simulation.auto_play:
            self.simulation.auto_play = False
            for id in self.simulation.frame_updates:
                self.after_cancel(id)
        else:
            self.simulation.frame_updates = []
            self.simulation.auto_play = True
            after_id = self.after(MILISECONDS_PER_FRAME, self.advance_step)
            self.simulation.frame_updates.append(after_id)
        self.update_auto_play_text()

    def advance_step(self):
        if self.simulation.auto_play:
            self.handle_time_adjustment(auto_play=True)
            self.after(MILISECONDS_PER_FRAME, self.advance_step)

    def update_following_body_text(self, body_name, body):
        following_text = f"Following: {body_name.upper()}"
        property_lines = []
        for property_name, property_value in vars(body).items():
            if property_name not in PROPERTIES_TO_EXCLUDE:
                property_print_name, units = property_name_and_units(property_name)
                if property_name in PROPERTIES_TO_ROUND:
                    property_value = format_with_thousands_separator(property_value, 0)
                if property_name in PROPERTIES_TO_FORMAT:
                    property_value = format_with_thousands_separator(property_value)
                line = f"    - {property_print_name}: {property_value} {units}"
                property_lines.append(line)
        object_properties_text = "Information:\n" + "\n".join(property_lines)
        self.widgets.canvas.itemconfigure(self.following_object, text=following_text)
        self.widgets.canvas.itemconfigure(self.following_object_info, text=object_properties_text)

    def update_spaceship_text(self, spaceship_name, spaceship):
        following_text = f"Following: {spaceship_name}"
        speed = spaceship.return_velocity_vector() - self.simulation.velocity_reference
        speed_module = sqrt(speed.x**2 + speed.y**2 + speed.z**2)
        object_properties_text = (f"Velocity x = {format_with_thousands_separator(speed.x, 2)} km/s\n"
                                  f"Velocity y = {format_with_thousands_separator(speed.y, 2)} km/s\n"
                                  f"Velocity z = {format_with_thousands_separator(speed.z, 2)} km/s\n"
                                  f"Velocity module = {format_with_thousands_separator(speed_module, 2)} km/s\n"
                                  f"Fuel mass (main) = {format_with_thousands_separator(spaceship.fuel_mass, 2)} kg\n"
                                  f"Fuel mass (takeoff) = {format_with_thousands_separator(spaceship.takeoff_fuel_mass, 2)} kg")
        self.widgets.canvas.itemconfigure(self.following_object, text=following_text)
        self.widgets.canvas.itemconfigure(self.following_object_info, text=object_properties_text)

    def on_canvas_resize(self, event):
        new_width = event.width
        new_height = event.height
        self.widgets.canvas.configure(width=new_width, height=new_height)
        self.widgets.canvas.itemconfig(self.widgets.button_window, window=self.widgets.setup_simulation_button)
        self.widgets.canvas.coords(self.widgets.button_window, self.widgets.canvas.winfo_reqwidth() - 10, 7)
        self.widgets.canvas.itemconfig(self.widgets.progress_bar_window, window=self.widgets.time_progress_bar)
        self.widgets.canvas.coords(self.widgets.progress_bar_window, 0, self.widgets.canvas.winfo_reqheight()-10)
        self.center_point_x, self.center_point_y = round(new_width/2), round(new_height/2)
        update_standard_draw_scale(self, new_width, new_height)
        update_distance_scale(self)
        draw_celestial_bodies(self)

    def handle_canvas_double_click(self, event):
        clicked_body_ids = self.widgets.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for object_name, body_id, text_id in self.body_ids:
            if body_id in clicked_body_ids or text_id in clicked_body_ids:
                self.simulation.update_following_object(object_name)
                update_standard_draw_scale(self, self.widgets.canvas.winfo_width(), self.widgets.canvas.winfo_height())
                draw_celestial_bodies(self)
                self.simulation.draw_spaceship_trajectories()
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
        if self.simulation.auto_play or event.keysym == "Right":
            self.simulation.step_date("up")
        elif event.keysym == "Left":
            self.simulation.step_date("down")

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
        self.simulation.draw_spaceship_trajectories()

    def change_time_step(self, event):
        if event.keysym=="Up":
            self.simulation.adjust_user_time_step("up")
        elif event.keysym=="Down":
            self.simulation.adjust_user_time_step("down")
        self.update_time_text()

    def save_positions(self):
        positions = {}
        for body_name, body_obj in self.simulation.celestial_bodies.items():
            positions[body_name] = {"x": body_obj.x,
                                    "y": body_obj.y,
                                    "z": body_obj.z}
        return positions

    def calculate_change_vectors(self, last_positions):
        change_vectors = {}
        for body_name, body_obj in self.simulation.celestial_bodies.items():
            change_vectors[body_name] = {"x": body_obj.x - last_positions[body_name]["x"],
                                         "y": body_obj.y - last_positions[body_name]["y"],
                                         "z": body_obj.z - last_positions[body_name]["z"]}
        return change_vectors

    def update_auto_play_text(self):
        auto_play_text = f"Auto run: {'Running' if self.simulation.auto_play else 'Stopped'}"
        self.widgets.canvas.itemconfigure(self.auto_play_text, text=auto_play_text, fill=AUTO_RUN_TEXT_COLOR_RUN if self.simulation.auto_play else AUTO_RUN_TEXT_COLOR_STOP)

    def update_time_text(self):
        time_step_name = self.simulation.user_time_step_name
        show_date = self.simulation.date.strftime('%Y-%m-%d %H:%M:%S')
        time_text = f"Current date: {show_date} - Time step = {time_step_name}"
        self.widgets.canvas.itemconfigure(self.time_text, text=time_text)

    def update_scale_text(self):
        scale_text = f"Scale: {self.modified_scale}"
        self.widgets.canvas.itemconfigure(self.scale_text, text=scale_text)

    def body_position(self, body_location_path, timestamp=None):
        position = [0, 0, 0]
        if timestamp==None:
            timestamp = self.simulation.timestamp
        for index in range(len(body_location_path) - 1):
            index1 = body_location_path[index]
            index2 = body_location_path[index + 1]
            step = self.kernel[index1, index2].compute(timestamp)
            position += step
        return position

    def body_velocity(self, body_location_path, timestamp=None):
        velocity = [0, 0, 0]
        if timestamp==None:
            timestamp = self.simulation.timestamp
        for index in range(len(body_location_path) - 1):
            index1 = body_location_path[index]
            index2 = body_location_path[index + 1]
            step_pos, step_vel = self.kernel[index1, index2].compute_and_differentiate(timestamp)
            velocity += step_vel/86400  # Default is km/day, convert to km/s
        velocity = Point(x=velocity[0], y=velocity[1], z=velocity[2])
        return velocity

    def body_position_and_velocity(self, body_location_path, timestamp=None):
        position = [0, 0, 0]
        velocity = [0, 0, 0]
        if timestamp==None:
            timestamp = self.simulation.timestamp
        for index in range(len(body_location_path) - 1):
            index1 = body_location_path[index]
            index2 = body_location_path[index + 1]
            step_pos, step_vel = self.kernel[index1, index2].compute_and_differentiate(timestamp)
            position += step_pos  # km/s
            velocity += step_vel/86400  # Default is km/day, convert to km/s
        position = Point(x=position[0], y=position[1], z=position[2])
        velocity = Point(x=velocity[0], y=velocity[1], z=velocity[2])
        return position, velocity

    def return_orbit_body_state(self, body_name, altitude,
                                  direction=DEFAULT_ORBIT_DIRECTION,
                                  angle_deg=0, eccentricity=0):
        body = self.simulation.celestial_bodies[body_name]
        state = SpaceshipState.orbit_planet_state(body, altitude, direction=direction,
                                                  angle_deg=angle_deg,
                                                  eccentricity=eccentricity)
        return state

    def print_all_bodies_positions(self):
        for body_name, body_obj in self.celestial_bodies.items():
            print(f"{body_name}: ({body_obj.x}, {body_obj.y}, {body_obj.z})")

    def load_orbits(self, resolution=ORBIT_RESOLUTION):
        for body_name, body_obj in self.simulation.celestial_bodies.items():
            body_obj.orbit_points = []
            period = body_obj.orbital_period
            if period > 0:
                time_step = period/resolution*JULIAN_DATE_DAY
                num_steps = round(period/time_step)
                parent_body = self.simulation.celestial_bodies.get(body_obj.parent_body)
                for i in range(num_steps+1):
                    date = MIN_JULIAN_DATE + i * time_step
                    if date <= MAX_JULIAN_DATE:
                        position = self.body_position(body_obj.location_path, date) - self.body_position(parent_body.location_path, date) + self.body_position(parent_body.location_path)
                        if not DRAW_3D:
                            body_obj.orbit_points.append((position[0], position[1]))
                        else:
                            body_obj.orbit_points.append((position[0], position[1], position[2]))

    def update_orbits(self, change_vectors):
        for body_name, body_obj in self.simulation.celestial_bodies.items():
            if body_obj.parent_body in change_vectors and not body_obj=="Sun":
                change_vector = change_vectors[body_obj.parent_body]
                for i in range(len(body_obj.orbit_points)):
                    body_obj.orbit_points[i] = (body_obj.orbit_points[i][0] + change_vector["x"],
                                                body_obj.orbit_points[i][1] + change_vector["y"],
                                                body_obj.orbit_points[i][2] + change_vector["z"] if DRAW_3D else 0)

    def update_all_bodies_positions(self):
        for body_name, body_obj in self.simulation.celestial_bodies.items():
            #position = self.body_position(body_obj.location_path)
            position, velocity = self.body_position_and_velocity(body_obj.location_path)
            self.simulation.celestial_bodies[body_name].x = position.x
            self.simulation.celestial_bodies[body_name].y = position.y
            self.simulation.celestial_bodies[body_name].z = position.z
            self.simulation.celestial_bodies[body_name].velocity_x = velocity.x
            self.simulation.celestial_bodies[body_name].velocity_y = velocity.y
            self.simulation.celestial_bodies[body_name].velocity_z = velocity.z

    def update_boundaries(self):
        max_x = max(abs(body.x-self.simulation.origin.x) for body in self.simulation.celestial_bodies.values())
        max_y = max(abs(body.y-self.simulation.origin.y) for body in self.simulation.celestial_bodies.values())
        self.max_distance_width = max_x
        self.max_distance_height = max_y
        if DRAW_3D:
            min_z = min(body.z for body in self.simulation.celestial_bodies.values())
            max_z = max(body.z for body in self.simulation.celestial_bodies.values())
            self.max_distance_depth = max_z - min_z


class Widgets(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(master=parent)
        self.configure(fg_color=DEFAULT_BACKGROUND)
        self.canvas = ctk.CTkCanvas(parent, bg="black", width=WINDOW_SIZE[0], height=WINDOW_SIZE[1])
        self.canvas.pack(fill="both", expand=True)
        self.setup_simulation_button = ctk.CTkButton(self.canvas, text="Setup simulation")
        self.button_window = self.canvas.create_window(self.canvas.winfo_reqwidth()-10,
                                                       7,
                                                       anchor=ctk.NE,
                                                       window=self.setup_simulation_button)
        self.time_progress_bar = ctk.CTkProgressBar(self.canvas)
        self.progress_bar_window = self.canvas.create_window(0,
                                                             self.canvas.winfo_reqheight()-10,
                                                             anchor=ctk.S,
                                                             window=self.time_progress_bar)
        # self.time_progress_bar.configure(height=10)
        # self.time_progress_bar.pack(expand=True, fill="x", side="bottom")
        # self.button_window = self.canvas.create_window()
        self.canvas.update_idletasks()


def main():
    root = App()
    root.mainloop()
    close_ephemeris_data(root)
    root.destroy

if __name__ == "__main__":
    main()