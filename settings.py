from math import pi
from functions import color_index_to_rgb

# Window settings
WINDOW_SIZE = (800, 500)
WINDOW_MIN_SIZE = (700, 400)
DEFAULT_BACKGROUND = "black"

ephemeris_file = "de421.bsp"
ephemeris_url = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp"

# Celestial body properties
SUN_STAR_TYPE = "G2V"
SUN_LUMINOSITY = 3.828e26       # W
SUN_RADIUS = 695700             # km
SUN_MASS = 1.9885e30            # kg
SUN_TEMPERATURE = 5772          # K
SUN_ROTATION_VELOCITY = 1.997    # km/s
SUN_COLOR_INDEX = 0.63
SUN_COLOR = color_index_to_rgb(SUN_COLOR_INDEX)
SUN_TEXTURE = None
SUN_CIRCUMFERENCE = 2*pi*SUN_RADIUS     # km
SUN_ROTATIONAL_PERIOD = SUN_CIRCUMFERENCE/SUN_ROTATION_VELOCITY # seconds