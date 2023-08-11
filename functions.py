import locale
from math import pi
from settings import MAX_JULIAN_DATE, MIN_JULIAN_DATE

def convert_to_julian_date(date, seconds=None, minutes=None,
                           hours=None, days=None, months=None, years=None):
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