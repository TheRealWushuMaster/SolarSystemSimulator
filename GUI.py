from settings import *
#import tkinter as tk
import customtkinter as ctk
from skyfield.api import load, Topos
import requests
import os
import email.utils
import classes

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Solar System Simulator")
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.resizable=(True, True)
        self.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])
        self.iconbitmap("logos/logo-2.ico")
        self.configure(fg_color = DEFAULT_BACKGROUND)
        
        self.check_update()

        Controls(self)
        
        self.create_bodies()

        self.mainloop()

    def check_update(self):
        if os.path.exists(ephemeris_file):
            current_timestamp = os.path.getmtime(ephemeris_file)
        else:
            current_timestamp = 0
        response = requests.head(ephemeris_url)
        #print(f"Response = {response}")
        if 'Last-Modified' in response.headers:
            latest_timestamp = response.headers['Last-Modified']
        else:
            latest_timestamp = 0
        
        latest_timestamp = email.utils.mktime_tz(email.utils.parsedate_tz(latest_timestamp))

        #print(f"Current timestamp: {current_timestamp}")
        #print(f"Latest timestamp: {latest_timestamp}")
        if current_timestamp < latest_timestamp:
            print("Downloading updated ephemeris file...")
            self.download_updated_ephemeris()
        else:
            print("Ephemeris file is up to date.")
    
    def download_updated_ephemeris(self):
        response = requests.get(ephemeris_url)
        with open(ephemeris_file, "wb") as file:
            file.write(response.content)
    
    def create_bodies(self):
        pass
        # sun = classes.Star(SUN_STAR_TYPE, 1, "Sun", 0, 0, SUN_RADIUS, SUN_MASS, SUN_TEMPERATURE,
        #                    SUN_ROTATIONAL_PERIOD, SUN_COLOR, SUN_TEXTURE)
        # mercury = classes.Planet(sun)
        # venus = classes.Planet(sun, 1)
        # earth = classes.Planet(sun, 1)

class Controls(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(master=parent)
        self.configure(fg_color=DEFAULT_BACKGROUND)
        canvas = ctk.CTkCanvas(parent, bg="black")

        canvas.pack(fill="both", expand=True)

App()