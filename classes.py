class Star():
    def __init__(self, name, x, y, radius, mass, temperature, star_type, luminosity,
                 rotation_period, color, texture=None, parent_body=None):
        self.name = name
        self.x = x
        self.y = y
        self.radius = radius
        self.mass = mass
        self.temperature = temperature
        self.rotation_period = rotation_period
        self.color = color
        self.texture = texture
        self.star_type = star_type
        self.luminosity = luminosity
        self.parent_body = parent_body

class Planet():
    def __init__(self, name, x, y, radius, mass, temperature, parent_body, planet_type,
                 rotation_period, color, texture=None, atmosphere=None, surface=None, rings=None):
        self.name = name
        self.x = x
        self.y = y
        self.radius = radius
        self.mass = mass
        self.temperature = temperature
        self.rotation_period = rotation_period
        self.color = color
        self.texture = texture
        self.parent_body = parent_body
        self.planet_type = planet_type
        self.atmosphere = atmosphere
        self.surface = surface
        self.parent_body = parent_body
        self.rings = rings