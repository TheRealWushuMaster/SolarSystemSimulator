from math import pi
import locale

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
    color_hex = f"#{r:02x}{g:02x}{b:02x}"
    return color_hex

def get_lighter_color(hex_color, lighten_factor=0.2):
    # Remove the '#' character from the hexadecimal color string
    hex_color = hex_color.lstrip("#")
    
    # Convert the hexadecimal color string to RGB values
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # Calculate the lighter shade of the color
    r_lighter = int(min(255, r + (255 - r) * lighten_factor))
    g_lighter = int(min(255, g + (255 - g) * lighten_factor))
    b_lighter = int(min(255, b + (255 - b) * lighten_factor))
    
    # Convert the lighter RGB values back to a hexadecimal color string
    hex_lighter = "#{:02x}{:02x}{:02x}".format(r_lighter, g_lighter, b_lighter)
    
    return hex_lighter

def calculate_additional_properties(data_dict, color=False):
    for star, data in data_dict.items():
        if color:
            data["COLOR"] = color_index_to_rgb(data["COLOR_INDEX"])
        data["CIRCUMFERENCE"] = round(2*pi*data["RADIUS"], 0)
        data["ROTATION_PERIOD"] = round(data["CIRCUMFERENCE"]/data["ROTATION_VELOCITY"], 0)

def format_with_thousands_separator(number):
    # Set the appropriate locale for formatting
    locale.setlocale(locale.LC_ALL, '')
    # Format the number with thousands separators
    formatted_number = locale.format_string("%d", number, grouping=True)
    return formatted_number