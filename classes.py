class Body():
    def __init__(self, name, x, y, radius, mass, temperature,
                 rotation_period, color, texture=None):
        self.name = name
        self.x = x
        self.y = y
        self.radius = radius
        self.mass = mass
        self.temperature = temperature
        self.rotation_period = rotation_period
        self.color = color
        self.texture = texture

class Star(Body):
    def __init__(self, star_type, luminosity, name, x, y, radius, mass, temperature,
                 rotation_period, color, texture=None):
        super().__init__(self, name, x, y, radius, mass, temperature,
                      rotation_period, color, texture=None)
        self.star_type = star_type
        self.luminosity = luminosity

class Planet(Body):
    def __init__(self, parent_body, planet_type, name, x, y, radius, mass, temperature,
                 rotation_period, color, texture=None, atmosphere=None, surface=None, ):
        super().__init__(self, name, x, y, radius, mass, temperature,
                      rotation_period, color, texture=None)
        self.parent_body = parent_body
        self.planet_type = planet_type
        self.atmosphere = atmosphere
        self.surface = surface