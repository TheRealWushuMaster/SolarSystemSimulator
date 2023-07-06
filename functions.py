from math import pi
import locale
#from settings import MAX_JULIAN_DATE, MIN_JULIAN_DATE
import settings

def color_index_to_rgb(color_index):
    color_temp = 4600 * ((1 / ((0.92 * color_index) + 1.7)) + (1 / ((0.92 * color_index) + 0.62)))
    if color_temp <=6600:
        r = 255
        g = max(0, min(255, int((color_temp - 2000) / 25)))
        b = 0
    else:
        r = max(0, min(255, int((color_temp - 6000) / 25)))
        g = max(0, min(255, int((color_temp - 4000) / 15)))
        b = max(0, min(255, int((color_temp - 2000) / 6)))
    color_hex = f"#{r:02x}{g:02x}{b:02x}".upper()
    return color_hex

def get_lighter_color(hex_color, lighten_factor=0.2):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r_lighter = int(min(255, r + (255 - r) * lighten_factor))
    g_lighter = int(min(255, g + (255 - g) * lighten_factor))
    b_lighter = int(min(255, b + (255 - b) * lighten_factor))
    hex_lighter = "#{:02x}{:02x}{:02x}".format(r_lighter, g_lighter, b_lighter)
    return hex_lighter

def calculate_additional_properties(data_dict, color=False):
    for item, data in data_dict.items():
        if color:
            data["COLOR"] = color_index_to_rgb(data["COLOR_INDEX"])
        data["CIRCUMFERENCE"] = round(2*pi*data["RADIUS"], 0)
        data["ROTATION_PERIOD"] = round(data["CIRCUMFERENCE"]/data["ROTATION_VELOCITY"], 0)
        data["ORBIT_POINTS"] = []

def format_with_thousands_separator(number, num_decimals=-1):
    locale.setlocale(locale.LC_ALL, '')
    if 'e' in str(number).lower():
        coeff, exponent = str(number).split('e')
        coeff = float(coeff)
    else:
        coeff = number
        exponent = 0
    if num_decimals == -1:
        decimal_symbol = locale.localeconv()['decimal_point']
        try:
            integer_part, decimal_part = str(coeff).split(".")
        except:
            integer_part = number
            decimal_part = ""
            decimal_symbol = ""
        formatted_integer_part = locale.format_string("%d", int(integer_part), grouping=True)
        formatted_number = f"{formatted_integer_part}{decimal_symbol}{decimal_part}"
    else:
        rounded_number = round(coeff, ndigits=num_decimals)
        if num_decimals in (None, 0):
            formatted_number = locale.format_string("%d", rounded_number, grouping=True)
        else:
            formatted_number = locale.format_string(f'%.{num_decimals}f', rounded_number, grouping=True)
    if exponent != 0:
        formatted_number = f"{formatted_number}e{exponent}"
    return formatted_number

def property_name_and_units(property_name):
    if property_name in ("radius", "circumference"):
        units = "km"
        if property_name == "radius":
            print_name = "Radius"
        else:
            print_name = "Circumference"
    elif property_name == "luminosity":
        units = "W"
        print_name = "Luminosity"
    elif property_name == "mass":
        units = "kg"
        print_name = "Mass"
    elif property_name == "temperature":
        units = "K"
        print_name = "Temperature"
    elif property_name == "rotation_velocity":
        units = "km/s"
        print_name = "Rotation velocity"
    elif property_name == "rotation_period":
        units = "s"
        print_name = "Rotation period"
    elif property_name == "star_type":
        units = ""
        print_name = "Star type"
    elif property_name == "parent_body":
        units = ""
        print_name = "Parent body"
    elif property_name == "color_index":
        units = ""
        print_name = "Color index"
    elif property_name == "color":
        units = ""
        print_name = "Color"
    elif property_name == "planet_type":
        units = ""
        print_name = "Planet type"
    elif property_name == "average_orbital_speed":
        units = "km/s"
        print_name = "Average orbital speed"
    elif property_name == "orbital_period":
        units = "days"
        print_name = "Orbital period"
    else:
        units = ""
        print_name = property_name
    return print_name, units

def calculate_orbit_parameters(name):
    max_orbits = 10
    max_step_size = {
        "Mercury": 5,
        "Venus": 10,
        "Earth": 15,
        "Mars": 20,
        "Jupiter": 30,
        "Saturn": 40,
        "Uranus": 50,
        "Neptune": 60,
        "Pluto": 70
    }
    step_size = max_step_size.get(name, 1)
    num_orbits = min(int((settings.MAX_JULIAN_DATE - settings.MIN_JULIAN_DATE) / step_size), max_orbits)
    return step_size, num_orbits
