from math import pi
from functions import calculate_additional_properties

# Window settings
WINDOW_SIZE = (800, 500)
WINDOW_MIN_SIZE = (700, 400)
DEFAULT_BACKGROUND = "black"

# JPL body information
EPHEMERIS_FILE = "de421.bsp"
EPHEMERIS_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp"
CHARON_FILE = "plu043.bsp"
CHARON_FILE_URL = "https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/plu043.bsp"
MAX_JULIAN_DATE = 2471184.5
MIN_JULIAN_DATE = 2414864.5
ALL_EPHEMERIS_DATA_URL = "https://ssd.jpl.nasa.gov/ephem.html"

# Units
AU = 149597870.7   # Astronomical unit in km
JULIAN_DATE_YEAR = 365.25
JULIAN_DATE_MONTH = 365.25/12
JULIAN_DATE_WEEK = 7
JULIAN_DATE_DAY = 1

# Graphical information
DRAW_3D = False
CANVAS_DRAW_PADDING = 20
TEXT_SIZE_INFO = 10
TEXT_SIZE_NAME = 10
INFO_TEXT_SEPARATION = 20
BODY_NAME_COLOR = "white"

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
        "COLOR": "0",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,             # km
        "ROTATION_PERIOD": 0,           # seconds
        "PARENT_BODY": None,
        "X": 0,
        "Y": 0,
        "Z": 0,
        "LOCATION_PATH": [0, 10],
        "ORBITAL_PERIOD": 1,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": 1
    }
}
calculate_additional_properties(Star_data, color=True)

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
        "ORBITAL_PERIOD": 87.9691,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 224.701,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 365.2563,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "LOCATION_PATH": [0, 4, 499],
        "ORBITAL_PERIOD": 686.98,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 4332.59,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 10759.22,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 30688.5,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 60195,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 90560,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
    },
}
calculate_additional_properties(Planet_data)

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
        "ORBITAL_PERIOD": 27.3217,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
    }
}
calculate_additional_properties(Moon_data)

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
        "ORBITAL_PERIOD": 204199,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 6.387,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
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
        "ORBITAL_PERIOD": 1680,
        "ORBIT_STEP": JULIAN_DATE_WEEK,
        "NUM_ORBIT_STEPS": JULIAN_DATE_WEEK/2
    }
}