class Star():
    def __init__(self, NAME, X, Y, Z, RADIUS, MASS, TEMPERATURE, STAR_TYPE, LUMINOSITY,
                 ROTATION_PERIOD, ROTATION_VELOCITY, COLOR_INDEX, COLOR, CIRCUMFERENCE,
                 TEXTURE=None, PARENT_BODY=None):
        self.name = NAME
        self.x = X
        self.y = Y
        self.z = Z
        self.radius = RADIUS
        self.mass = MASS
        self.temperature = TEMPERATURE
        self.rotation_period = ROTATION_PERIOD
        self.rotation_velocity = ROTATION_VELOCITY
        self.color_index = COLOR_INDEX
        self.color = COLOR
        self.circumference = CIRCUMFERENCE
        self.texture = TEXTURE
        self.star_type = STAR_TYPE
        self.luminosity = LUMINOSITY
        self.parent_body = PARENT_BODY

    def __str__(self):
        return f"Star(name={self.name}, x={self.x}, y={self.y}, z={self.z}, radius={self.radius}, mass={self.mass}, temperature={self.temperature}, rotation_period={self.rotation_period}, rotation_velocity={self.rotation_velocity}, color_index={self.color_index}, color={self.color}, circumference={self.circumference}, texture={self.texture}, star_type={self.star_type}, luminosity={self.luminosity}, parent_body={self.parent_body})"


class Planet():
    def __init__(self, NAME, X, Y, Z, RADIUS, MASS, TEMPERATURE, PARENT_BODY, PLANET_TYPE,
                 ROTATION_VELOCITY, ROTATION_PERIOD, COLOR, CIRCUMFERENCE, 
                 TEXTURE=None, ATMOSPHERE=None, SURFACE=None, RINGS=0):
        self.name = NAME
        self.x = X
        self.y = Y
        self.z = Z
        self.radius = RADIUS
        self.mass = MASS
        self.temperature = TEMPERATURE
        self.rotation_velocity = ROTATION_VELOCITY
        self.rotation_period = ROTATION_PERIOD
        self.color = COLOR
        self.circumference = CIRCUMFERENCE
        self.texture = TEXTURE
        self.parent_body = PARENT_BODY
        self.planet_type = PLANET_TYPE
        self.atmosphere = ATMOSPHERE
        self.surface = SURFACE
        self.rings = RINGS
    
    def __str__(self):
        return f"Planet(name={self.name}, x={self.x}, y={self.y}, z={self.z}, radius={self.radius}, mass={self.mass}, temperature={self.temperature}, rotation_velocity={self.rotation_velocity}, rotation_period={self.rotation_period}, color={self.color}, circumference={self.circumference}, texture={self.texture}, parent_body={self.parent_body}, planet_type={self.planet_type}, atmosphere={self.atmosphere}, surface={self.surface}, rings={self.rings})"
