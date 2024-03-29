# Window settings
WINDOW_SIZE = (800, 500)
WINDOW_MIN_SIZE = (700, 400)
DEFAULT_BACKGROUND = "black"
WINDOW_LOGO = "logos/logo-2.ico"

# JPL body information
EPHEMERIS_FILE = "de440t.bsp"
EPHEMERIS_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440t.bsp"
MAX_JULIAN_DATE = 2688976.5
MIN_JULIAN_DATE = 2287184.5
MARS_FILE = "mar097.bsp"
MARS_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/mar097.bsp"
JUPITER_FILE = "jup365.bsp"
JUPITER_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/jup365.bsp"
SATURN_FILE = "sat441l.bsp"
SATURN_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/sat441l.bsp"
URANUS_FILE = "ura111.bsp"
URANUS_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/ura111.bsp"
NEPTUNE_FILE = "nep102.bsp"
NEPTUNE_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/nep102.bsp"
PLUTO_FILE = "plu043.bsp"
PLUTO_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/plu043.bsp"
ALL_EPHEMERIS_DATA_URL = "https://ssd.jpl.nasa.gov/ephem.html"
PLANETARY_SATELLITE_EPHEMERIDES_URL = "https://ssd.jpl.nasa.gov/sats/ephem/files.html"

# Units
AU = 149597870.7   # Astronomical unit in km
JULIAN_DATE_YEAR = 365.25
JULIAN_DATE_MONTH = 365.25/12
JULIAN_DATE_WEEK = 7
JULIAN_DATE_DAY = 1
JULIAN_DATE_12_HOURS = JULIAN_DATE_DAY/2
JULIAN_DATE_HOUR = JULIAN_DATE_12_HOURS/12
JULIAN_DATE_30_MINUTES = JULIAN_DATE_HOUR/2
JULIAN_DATE_15_MINUTES = JULIAN_DATE_30_MINUTES/2
JULIAN_DATE_MINUTE = JULIAN_DATE_15_MINUTES/15
JULIAN_DATE_10_SECONDS = JULIAN_DATE_MINUTE/6
JULIAN_DATE_SECOND = JULIAN_DATE_10_SECONDS/10

# Graphical information
DRAW_3D = True
CANVAS_DRAW_PADDING = 20
DEFAULT_FONT = "Arial"
TEXT_SIZE_INFO = 10
TEXT_SIZE_NAME = 10
DEFAULT_NAME_TEXT_PADDING = 10
DEFAULT_FONT_COLOR = "white"
SCALE_TEXT_COLOR = "yellow"
AUTO_RUN_TEXT_COLOR_RUN = "red"
AUTO_RUN_TEXT_COLOR_STOP = "green"
FOLLOWING_OBJECT_TEXT_COLOR = "green"
DISTANCE_REFERENCE_TEXT_COLOR = "cyan"
VELOCITY_REFERENCE_TEXT_COLOR = "cyan"
INFO_TEXT_SEPARATION = 20
BODY_NAME_COLOR = "white"
ORBIT_FILL_COLOR = "#222222"
ORBIT_RESOLUTION = 50
ROTATION_SENSITIVITY = 0.005
FRAMES_PER_SECOND = 10
MILISECONDS_PER_FRAME = round(1000/FRAMES_PER_SECOND)
PROPERTIES_TO_EXCLUDE = ["name", "x", "y", "z", "location_path", "texture", "rings", "surface",
                         "atmosphere", "orbit_points", "orbit_resolution", "num_orbit_steps",
                         "velocity_x", "velocity_y", "velocity_z"]
PROPERTIES_TO_FORMAT = ["luminosity", "radius", "mass", "temperature", "rotation_velocity",
                        "color_index", "average_orbital_speed", "orbital_period"]
PROPERTIES_TO_ROUND = ["rotation_period", "circumference"]

# Simulation parameters
G = 6.674e-11
ARRIVAL_DISTANCE = 2    # Number of radiuses from the planet to consider "arrived" at the planet
AVERAGE_RADIATION_ANGLE = 45
c = 299792458   # m/s
DEFAULT_TIME_STEP = JULIAN_DATE_DAY/24  # 1 hour
BOOST_TIME_STEP = JULIAN_DATE_DAY/24/60 # 1 minute
COAST_TIME_STEP = JULIAN_DATE_DAY/24/6  # 10 minutes
SPACESHIP_COLOR = "gray"
SPACESHIP_BORDER = "white"
DEFAULT_ORBIT_DIRECTION = "cw"
DEFAULT_SMALL_TIME_STEP = 10  # Seconds
DEFAULT_MEDIUM_TIME_STEP = 5*60  # 5 minutes in seconds
DEFAULT_LARGE_TIME_STEP = 30*60  # 30 minutes in seconds
simulation_steps = [("1 second", 1),        # 1 second
                    ("10 seconds", 10),     # 10 seconds
                    ("1 minute", 60),       # 1 minute
                    ("15 minutes", 900),    # 15 minutes (60 * 15)
                    ("30 minutes", 1800),   # 30 minutes (60 * 30)
                    ("1 hour", 3600),       # 1 hour (60 * 60)
                    ("12 hours", 43200),    # 12 hours (60 * 60 * 12)
                    ("1 day", 86400),       # 1 day (60 * 60 * 24)
                    ("1 week", 604800),     # 1 week (60 * 60 * 24 * 7)
                    ("1 month", 2592000),   # 1 month (60 * 60 * 24 * 30)
                    ("1 year", 31536000)]   # 1 year (60 * 60 * 24 * 365)
# When simulating, consider that "month" and "year" time steps are not perfect
# multiples of some other time steps, which can be a problem when simulating
# multiple instructions per simulation time step.

# =========================
# Celestial body properties
# =========================
Star_data = {
    "Sun": {
        "STAR_TYPE": "G2V",
        "LUMINOSITY": 3.828e26,         # W
        "RADIUS": 695700,               # km
        "MASS": 1.9885e30,              # kg
        "TEMPERATURE": 5772,            # K
        "ROTATION_VELOCITY": 1.997,     # km/s
        "COLOR_INDEX": 0.63,
        "COLOR": "0",                   # hexadecimal
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,             # km
        "ROTATION_PERIOD": 0,           # seconds
        "PARENT_BODY": None,
        "X": 0,                         # km
        "Y": 0,                         # km
        "Z": 0,                         # km
        "LOCATION_PATH": [0, 10],
        "AVERAGE_ORBITAL_SPEED": 1,     # km/s
        "ORBITAL_PERIOD": 0             # days
    }
}

Planet_data = {
    "Mercury": {
        "PLANET_TYPE": "Rocky",
        "RADIUS": 2440,
        "MASS": 3.3e23,
        "TEMPERATURE": 440,
        "ROTATION_VELOCITY": 1.5,
        "COLOR": "#8C8887",    #"#BEBEBE",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 1, 199],
        "AVERAGE_ORBITAL_SPEED": 47.36,
        "ORBITAL_PERIOD": 87.9691
    },
    "Venus": {
        "PLANET_TYPE": "Rocky",
        "RADIUS": 6052,
        "MASS": 4.87e24,
        "TEMPERATURE": 737,
        "ROTATION_VELOCITY": 1.2,
        "COLOR": "#EEF0E8",    #"#FFA500",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 2, 299],
        "AVERAGE_ORBITAL_SPEED": 35.02,
        "ORBITAL_PERIOD": 224.701
    },
    "Earth": {
        "PLANET_TYPE": "Rocky",
        "RADIUS": 6371,
        "MASS": 5.97e24,
        "TEMPERATURE": 288,
        "ROTATION_VELOCITY": 0.465,
        "COLOR": "#2B5182",    #"#0000FF",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 3, 399],
        "AVERAGE_ORBITAL_SPEED": 29.7827,
        "ORBITAL_PERIOD": 365.2563
    },
    "Mars": {
        "PLANET_TYPE": "Rocky",
        "RADIUS": 3389,
        "MASS": 6.42e23,
        "TEMPERATURE": 210,
        "ROTATION_VELOCITY": 0.24,
        "COLOR": "#E19E68",    #"#FF4500",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 4], #, 499],
        "AVERAGE_ORBITAL_SPEED": 24.07,
        "ORBITAL_PERIOD": 686.98
    },
    "Jupiter": {
        "PLANET_TYPE": "Gas giant",
        "RADIUS": 69911,
        "MASS": 1.9e27,
        "TEMPERATURE": 165,
        "ROTATION_VELOCITY": 12.6,
        "COLOR": "#BFA189",    #"#FFD700",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 1,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 5],
        "AVERAGE_ORBITAL_SPEED": 13.07,
        "ORBITAL_PERIOD": 4332.59
    },
    "Saturn": {
        "PLANET_TYPE": "Gas giant",
        "RADIUS": 58232,
        "MASS": 5.7e26,
        "TEMPERATURE": 134,
        "ROTATION_VELOCITY": 9.9,
        "COLOR": "#C6A16D", #"#E5C73C",    #DAA520",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 3,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 6],
        "AVERAGE_ORBITAL_SPEED": 9.68,
        "ORBITAL_PERIOD": 10759.22
    },
    "Uranus": {
        "PLANET_TYPE": "Ice giant",
        "RADIUS": 25362,
        "MASS": 8.7e25,
        "TEMPERATURE": 76,
        "ROTATION_VELOCITY": 2.6,
        "COLOR": "#A7B7C4",    #"#00BFFF",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 1,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 7],
        "AVERAGE_ORBITAL_SPEED": 6.80,
        "ORBITAL_PERIOD": 30688.5
    },
    "Neptune": {
        "PLANET_TYPE": "Ice giant",
        "RADIUS": 24622,
        "MASS": 1.02e26,
        "TEMPERATURE": 72,
        "ROTATION_VELOCITY": 2.1,
        "COLOR": "#85A7D4",    #"#00008B",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 1,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 8],
        "AVERAGE_ORBITAL_SPEED": 5.43,
        "ORBITAL_PERIOD": 60195
    },
    "Pluto": {
        "PLANET_TYPE": "Dwarf",
        "RADIUS": 1188,
        "MASS": 1.3e22,
        "TEMPERATURE": 44,
        "ROTATION_VELOCITY": 6.4,
        "COLOR": "#E4D5C0",    #"#D9D9D9",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATION_PERIOD": 0,
        "RINGS": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 9],
        "AVERAGE_ORBITAL_SPEED": 4.743,
        "ORBITAL_PERIOD": 90560
    },
}

Moon_data = {
    "Moon": {
        "PARENT_BODY": "Earth",
        "PLANET_TYPE": "Rocky moon",
        "RADIUS": 1737,
        "MASS": 7.34e22,
        "TEMPERATURE": -20,
        "ROTATION_VELOCITY": 0.98,
        "ROTATION_PERIOD": 0,
        "COLOR": "#656160",    #"#D3D3D3",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "RINGS": 0,
        "LOCATION_PATH": [0, 3, 301],
        "AVERAGE_ORBITAL_SPEED": 1.022,
        "ORBITAL_PERIOD": 27.321661
    }
}

# Info on other bodies for future representation
Other_bodies = {
    "Eris": {
        "PLANET_TYPE": "Dwarf",
        "RADIUS": 1163,
        "MASS": 1.7e22,
        "TEMPERATURE": 30,
        "ROTATION_VELOCITY": 1.08,
        "COLOR": "#E0E0E0",
        "TEXTURE": None,
        "CIRCUMFERENCE": None,
        "ROTATION_PERIOD": 0,
        "RINGS": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "PARENT_BODY": 'Sun',
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "LOCATION_PATH": [0, 0],
        "AVERAGE_ORBITAL_SPEED": 3.434,
        "ORBITAL_PERIOD": 204199
    },
    "Charon": {
        "PARENT_BODY": "Pluto",
        "PLANET_TYPE": "Rocky moon",
        "RADIUS": 606,
        "MASS": 1.52e21,
        "TEMPERATURE": 53,
        "ROTATION_VELOCITY": 6.38,
        "ROTATION_PERIOD": 0,
        "COLOR": "#8E8D8B",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "RINGS": 0,
        "LOCATION_PATH": [0, 9, 901],
        "AVERAGE_ORBITAL_SPEED": 0.21,
        "ORBITAL_PERIOD": 6.387
    },
    "Ceres": {
        "PARENT_BODY": "Sun",
        "PLANET_TYPE": "Dwarf",
        "RADIUS": 939,
        "MASS": 9.38392e20,
        "TEMPERATURE": 172,
        "ROTATION_VELOCITY": 0.09261,
        "ROTATION_PERIOD": 0,
        "COLOR": "#8E8D8B",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "ATMOSPHERE": 0,
        "SURFACE": 0,
        "RINGS": 0,
        "LOCATION_PATH": [0, 0],
        "AVERAGE_ORBITAL_SPEED": 17.9,
        "ORBITAL_PERIOD": 1680
    }
}