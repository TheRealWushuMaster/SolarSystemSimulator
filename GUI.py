from settings import *
import customtkinter as ctk
import requests
import os
import email.utils
import classes
from jplephem.spk import SPK
import datetime
from functions import get_lighter_color

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.widgets = self.configure_app_window()
        self.widgets.canvas.bind("<Configure>", self.on_canvas_resize)
        self.widgets.canvas.bind("<MouseWheel>", self.handle_mousewheel)
        self.bind("<Left>", self.handle_time_adjustment)
        self.bind("<Right>", self.handle_time_adjustment)

        self.check_ephemeris_file_update()
        self.kernel = self.load_ephemeris_data()
        
        self.celestial_bodies = self.create_bodies()
        
        self.date = datetime.datetime.now()
        self.timestamp_months = 0
        self.timestamp_years = 0
        self.timestamp = self.convert_to_julian_date()

        self.update_all_bodies_positions()
        #self.print_all_bodies_positions()

        self.modified_scale = 1.0
        self.original_scale = self.calculate_standard_draw_scale(self.widgets.canvas.winfo_reqwidth()-4, self.widgets.canvas.winfo_reqheight()-4)
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

    def check_ephemeris_file_update(self):
        if os.path.exists(ephemeris_file):
            current_timestamp = os.path.getmtime(ephemeris_file)
        else:
            current_timestamp = 0
        response = requests.head(ephemeris_url)

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
        response = requests.get(ephemeris_url)
        with open(ephemeris_file, "wb") as file:
            file.write(response.content)

    def load_ephemeris_data(self):
        kernel = SPK.open('de421.bsp')
        return kernel
    
    def close_ephemeris_data(self, kernel):
        kernel.close()

    def create_bodies(self):
        celestial_bodies = {}
        # Create stars
        for star_name, star_properties in Star_data.items():
            star = classes.Star(star_name, **star_properties)
            celestial_bodies[star_name] = star
        # Create planets
        for planet_name, planet_properties in Planet_data.items():
            planet = classes.Planet(planet_name, **planet_properties)
            celestial_bodies[planet_name] = planet
        # Create moons
        #for moon_name, moon_properties in Moon_data.items():
        #    moon = classes.Planet(moon_name, **moon_properties)
        #    celestial_bodies[moon_name] = moon
        return celestial_bodies

    def calculate_standard_draw_scale(self, canvas_width, canvas_height):
        min_x = min(body.x for body in self.celestial_bodies.values())
        max_x = max(body.x for body in self.celestial_bodies.values())
        min_y = min(body.y for body in self.celestial_bodies.values())
        max_y = max(body.y for body in self.celestial_bodies.values())
        #min_z = min(body.z for body in bodies.values())
        #max_z = max(body.z for body in bodies.values())
        max_width = max_x - min_x
        max_height = max_y - min_y
        #max_depth = max_z - min_z
        draw_scale = min(canvas_width/max_width, canvas_height/max_height)
        return draw_scale

    def draw_celestial_bodies(self):
        center_point_x = round(self.widgets.canvas.winfo_reqwidth()/2)
        center_point_y = round(self.widgets.canvas.winfo_reqheight()/2)
        distance_scale = .7*self.original_scale*self.modified_scale
        radius_scale = 10*self.original_scale*self.modified_scale
        self.widgets.canvas.delete("all")
        time_text = f"Current date: {self.date} - adjustment {self.timestamp_months} months, {self.timestamp_years} years"
        scale_text = f"Scale: {self.modified_scale}"
        self.widgets.canvas.create_text(10, 10, anchor="nw", fill="white", text=time_text, font=("Arial", 8))
        self.widgets.canvas.create_text(10, 25, anchor="nw", fill="white", text=scale_text, font=("Arial", 8))
        for body in self.celestial_bodies.values():
            x = round(body.x * distance_scale + center_point_x)
            y = round(body.y * distance_scale + center_point_y)
            radius = max(round(body.radius * radius_scale * distance_scale), 3)
            self.widgets.canvas.create_oval(x-radius, y-radius, x + radius, y + radius, fill=body.color, outline=get_lighter_color(body.color))
            self.widgets.canvas.create_text(x + radius + 10, y, anchor='w', text=body.name, fill="white", font=("Arial", 8))
            #print(f"{body.name}: x={body.x}, x={x}norm, y={body.y}, y={y}norm, radius={body.radius}, radius={radius}norm")

    def on_canvas_resize(self, event):
        new_width = event.width-4
        new_height = event.height-4
        self.widgets.canvas.configure(width=new_width, height=new_height)
        self.original_scale = self.calculate_standard_draw_scale(new_width, new_height)
        self.draw_celestial_bodies()

    def handle_mousewheel(self, event):
        if event.state & 0x1:  # Check if Shift key is pressed
            if event.delta > 0:
                scale_factor = 0.1  # Increase scale by 0.1 for fine-grained zoom in
            else:
                scale_factor = -0.1  # Decrease scale by 0.1 for fine-grained zoom out
        else:
            if event.delta > 0:
                scale_factor = 1.0  # Increase scale by 1 for regular zoom in
            else:
                scale_factor = -1.0  # Decrease scale by 1 for regular zoom out
        # Apply the scale factor to adjust the scale of the representation
        self.modified_scale = round(self.modified_scale + scale_factor, 1)
        if self.modified_scale < 0.1:
            self.modified_scale = 0.1
        self.draw_celestial_bodies()

    def handle_time_adjustment(self, event):
        # Check if the Shift key is pressed
        fine_adjustment = event.state & 0x1
        # Update the timestamp based on the time step
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
        # Recalculate the positions of celestial bodies based on the updated timestamp
        self.timestamp = self.convert_to_julian_date()
        self.update_all_bodies_positions()
        # Redraw the canvas
        self.draw_celestial_bodies()

    def body_position(self, kernel, body):
        position = [0, 0, 0]
        #print(body.location_path)
        for index in range(len(body.location_path) - 1):
            index1 = body.location_path[index]
            index2 = body.location_path[index + 1]
            step = kernel[index1, index2].compute(self.timestamp)
            position += step
        return position

    def print_all_bodies_positions(self):
        for body_name, body_obj in self.celestial_bodies.items():
            print(f"{body_name}: ({body_obj.x}, {body_obj.y}, {body_obj.z})")
    
    def update_all_bodies_positions(self):
        for body_name, body_obj in self.celestial_bodies.items():
            position = self.body_position(self.kernel, body_obj)
            self.celestial_bodies[body_name].x = position[0]
            self.celestial_bodies[body_name].y = position[1]
            self.celestial_bodies[body_name].z = position[2]

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
        if julian_date < 2414864.5:
            julian_date = 2414864.5
        elif julian_date > 2471184.5:
            julian_date = 2471184.5
        return julian_date

class Widgets(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(master=parent)
        self.configure(fg_color=DEFAULT_BACKGROUND)
        self.canvas = ctk.CTkCanvas(parent, bg="black", width=WINDOW_SIZE[0], height=WINDOW_SIZE[1])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.update_idletasks()

root = App()
root.mainloop()
root.destroy