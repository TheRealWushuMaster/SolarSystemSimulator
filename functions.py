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