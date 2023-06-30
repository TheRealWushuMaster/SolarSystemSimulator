from math import pi
from functions import color_index_to_rgb, calculate_additional_properties

# Window settings
WINDOW_SIZE = (800, 500)
WINDOW_MIN_SIZE = (700, 400)
DEFAULT_BACKGROUND = "black"

ephemeris_file = "de421.bsp"
ephemeris_url = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp"

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
        "ROTATIONAL_PERIOD": 0          # seconds
    }
}
calculate_additional_properties(Star_data, color=True)

Planet_data = {
    "Mercury": {
        "TYPE": "Rocky",
        "RADIUS": 2440,
        "MASS": 3.3e23,
        "TEMPERATURE": 440,
        "ROTATION_VELOCITY": 1.5,
        "COLOR": "#BEBEBE",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": None
    },
    "Venus": {
        "TYPE": "Rocky",
        "RADIUS": 6052,
        "MASS": 4.87e24,
        "TEMPERATURE": 737,
        "ROTATION_VELOCITY": 1.2,
        "COLOR": "#FFA500",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": None
    },
    "Earth": {
        "TYPE": "Rocky",
        "RADIUS": 6371,
        "MASS": 5.97e24,
        "TEMPERATURE": 288,
        "ROTATION_VELOCITY": 0.465,
        "COLOR": "#0000FF",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": None
    },
    "Mars": {
        "TYPE": "Rocky",
        "RADIUS": 33990,
        "MASS": 6.42e23,
        "TEMPERATURE": 210,
        "ROTATION_VELOCITY": 0.24,
        "COLOR": "#FF4500",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": None
    },
    "Jupiter": {
        "TYPE": "Gas giant",
        "RADIUS": 69911,
        "MASS": 1.9e27,
        "TEMPERATURE": 165,
        "ROTATION_VELOCITY": 12.6,
        "COLOR": "#FFD700",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": 2
    },
    "Saturn": {
        "TYPE": "Gas giant",
        "RADIUS": 58232,
        "MASS": 5.7e26,
        "TEMPERATURE": 134,
        "ROTATION_VELOCITY": 9.9,
        "COLOR": "#DAA520",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": 3
    },
    "Uranus": {
        "TYPE": "Ice giant",
        "RADIUS": 25362,
        "MASS": 8.7e25,
        "TEMPERATURE": 76,
        "ROTATION_VELOCITY": 2.6,
        "COLOR": "#00BFFF",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": 1
    },
    "Neptune": {
        "TYPE": "Ice giant",
        "RADIUS": 24622,
        "MASS": 1.02e26,
        "TEMPERATURE": 72,
        "ROTATION_VELOCITY": 2.1,
        "COLOR": "#00008B",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": 1
    },
    "Pluto": {
        "TYPE": "Dwarf",
        "RADIUS": 1188,
        "MASS": 1.3e22,
        "TEMPERATURE": 44,
        "ROTATION_VELOCITY": 6.4,
        "COLOR": "#D9D9D9",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0,
        "ROTATIONAL_PERIOD": 0,
        "RINGS": None
    },
    "Eris": {
        "TYPE": "Dwarf",
        "RADIUS": 1163,
        "MASS": 1.7e22,
        "TEMPERATURE": 30,
        "ROTATION_VELOCITY": 1.08,
        "COLOR": "#D9D9D9",
        "TEXTURE": None,
        "CIRCUMFERENCE": None,
        "RINGS": None
    }
}
calculate_additional_properties(Planet_data)

Moon_data = {
    "Moon": {
        "PARENT_BODY": "Earth",
        "TYPE": "Rocky",
        "RADIUS": 1737.1,
        "MASS": 7.34e22,
        "TEMPERATURE": -20,
        "ROTATION_VELOCITY": 0.98,
        "COLOR": "#D3D3D3",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0
    },
    "Charon": {
        "PARENT_BODY": "Pluto",
        "TYPE": "Rocky",
        "RADIUS": 606,
        "MASS": 1.52e21,
        "TEMPERATURE": -233,
        "ROTATION_VELOCITY": 6.38,
        "COLOR": "#D3D3D3",
        "TEXTURE": None,
        "CIRCUMFERENCE": 0
    }
}
calculate_additional_properties(Moon_data)