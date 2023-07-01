from settings import *
import customtkinter as ctk
from skyfield.api import load, Topos
import requests
import os
import email.utils
import classes
from jplephem.spk import SPK
from jplephem import Ephemeris
import vtk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Solar System Simulator")
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.resizable=(True, True)
        self.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])
        self.iconbitmap("logos/logo-2.ico")
        self.configure(fg_color = DEFAULT_BACKGROUND)
        # Verify ephemeris updates
        self.check_ephemeris_file_update()
        #self.load_ephemeris_data()
        # Create widgets
        Widgets(self)
        # Create celestial bodies        
        celestial_bodies = self.create_bodies()
        # Draw celestial bodies
        #self.draw_celestial_bodies(celestial_bodies, Widgets.canvas)
        # Start main loop
        self.mainloop()

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
        #eph = Ephemeris(de421='de421.bsp')
        return kernel
    
    def close_ephemeris_data(self, kernel):
        kernel.close()

    def create_bodies(self):
        celestial_bodies = {}
        # Create stars
        for star_name, star_props in Star_data.items():
            star = classes.Star(star_name, **star_props)
            celestial_bodies[star_name] = star
        # Create planets
        for planet_name, planet_properties in Planet_data.items():
            planet = classes.Planet(planet_name, **planet_properties)
            celestial_bodies[planet_name] = planet
        # Create moons
        for moon_name, moon_properties in Moon_data.items():
            #parent_body = celestial_bodies[moon_properties['PARENT_BODY']]  # Get the parent body object
            moon = classes.Planet(moon_name, **moon_properties)
            celestial_bodies[moon_name] = moon
        return celestial_bodies

    def draw_celestial_bodies(self, celestial_bodies, canvas):
        pass

class Widgets(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(master=parent)
        self.configure(fg_color=DEFAULT_BACKGROUND)
        self.canvas = ctk.CTkCanvas(parent, bg="black")
        self.canvas.pack(fill="both", expand=True)
        # Create the 3D render window with vtk
        # renderer = vtk.vtkRenderer()
        # self.render_window = vtk.vtkRenderWindow()
        # self.render_window.AddRenderer(renderer)
        # self.render_window.SetSize(100, 100)
        # renderer.SetBackground(0, 0, 0)
        # interactor = vtk.vtkRenderWindowInteractor()
        # interactor.SetRenderWindow(self.render_window)
        # self.render_window.Render()
        # interactor.Start()

App()