from math import sqrt
from settings import G
#from orbital_functions import calculate_total_gravitational_acceleration

class Star():
    def __init__(self, NAME, X, Y, Z, RADIUS, MASS, TEMPERATURE, STAR_TYPE, LUMINOSITY,
                 ROTATION_PERIOD, ROTATION_VELOCITY, COLOR_INDEX, COLOR, CIRCUMFERENCE,
                 LOCATION_PATH, AVERAGE_ORBITAL_SPEED, ORBITAL_PERIOD,ORBIT_POINTS,
                 TEXTURE=None, PARENT_BODY=None, RINGS=0):
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
        self.location_path = LOCATION_PATH
        self.rings = RINGS
        self.average_orbital_speed = AVERAGE_ORBITAL_SPEED
        self.orbital_period = ORBITAL_PERIOD
        self.orbit_points = ORBIT_POINTS

    def __str__(self):
        return (f"Star(name={self.name}\nx={self.x}\ny={self.y}\nz={self.z}\nradius={self.radius}\nmass={self.mass}\n"
                f"temperature={self.temperature}\nrotation_period={self.rotation_period}\nrotation_velocity={self.rotation_velocity}\n"
                f"color_index={self.color_index}\ncolor={self.color}\ncircumference={self.circumference}\ntexture={self.texture}\n"
                f"star_type={self.star_type}\nluminosity={self.luminosity}\nparent_body={self.parent_body})")

class Planet():
    def __init__(self, NAME, X, Y, Z, RADIUS, MASS, TEMPERATURE, PARENT_BODY, PLANET_TYPE,
                 LOCATION_PATH, ROTATION_VELOCITY, ROTATION_PERIOD, COLOR, CIRCUMFERENCE, 
                 AVERAGE_ORBITAL_SPEED, ORBITAL_PERIOD, ORBIT_POINTS,
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
        self.location_path = LOCATION_PATH
        self.average_orbital_speed = AVERAGE_ORBITAL_SPEED
        self.orbital_period = ORBITAL_PERIOD
        self.orbit_points = ORBIT_POINTS
    
    def __str__(self):
        return (f"Planet(name={self.name}\nx={self.x}\ny={self.y}\nz={self.z}\nradius={self.radius}\nmass={self.mass}\n"
                f"temperature={self.temperature}\nrotation_velocity={self.rotation_velocity}\nrotation_period={self.rotation_period}\n"
                f"color={self.color}\ncircumference={self.circumference}\ntexture={self.texture}\nparent_body={self.parent_body}\n"
                f"planet_type={self.planet_type}\natmosphere={self.atmosphere}\nsurface={self.surface}\nrings={self.rings})")

class Point():
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Spaceship():
    def __init__(self, structure_mass, fuel_mass, payload_mass,
                 propulsion_system, radiation_reflectivity, surface_area,
                 x=0, y=0, z=0, velocity_x=0, velocity_y=0, velocity_z=0,
                 acceleration_x=0, acceleration_y=0, acceleration_z=0, size=0.1):
        self.x = x
        self.y = y
        self.z = z
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.velocity_z = velocity_z
        self.acceleration_x = acceleration_x
        self.acceleration_y = acceleration_y
        self.acceleration_z = acceleration_z
        self.total_mass = structure_mass + fuel_mass + payload_mass
        self.structure_mass = structure_mass
        self.fuel_mass = fuel_mass
        self.payload_mass = payload_mass
        self.propulsion_system = propulsion_system
        self.radiation_reflectivity = radiation_reflectivity
        self.surface_area = surface_area
        self.size = size
        self.reset_values()
    
    def reset_values(self):
        self.positions = []
        self.velocities = []
        self.accelerations = []
        self.thrust_vectors = []
        self.throttles = []
        self.fuel_masses = []

    def update_status(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step, bodies):
        thrust_module = self.propulsion_system.calculate_thrust(throttle)
        thrust_x = thrust_vector_x * thrust_module
        thrust_y = thrust_vector_y * thrust_module
        thrust_z = thrust_vector_z * thrust_module
        print(thrust_x, thrust_y, thrust_z)
        gravitational_acceleration_x, gravitational_acceleration_y, gravitational_acceleration_z = self.calculate_total_gravitational_acceleration(self, bodies)
        self.update_acceleration(thrust_x, thrust_y, thrust_z,
                                 gravitational_acceleration_x, gravitational_acceleration_y, gravitational_acceleration_z)
        self.update_mass(thrust_module, time_step)
        self.update_velocity(time_step)
        self.update_position(time_step)
        self.store_values(throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z)

    def store_values(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z):
        self.positions.append((self.x, self.y, self.z))
        self.velocities.append((self.velocity_x, self.velocity_y, self.velocity_z))
        self.accelerations.append((self.acceleration_x, self.acceleration_y, self.acceleration_z))
        self.thrust_vectors.append((thrust_vector_x, thrust_vector_y, thrust_vector_z))
        self.throttles.append(throttle)
        self.fuel_masses.append(self.fuel_mass)

    def update_mass(self, thrust_module, time_step):
        fuel_consumed = self.propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
        if self.fuel_mass > fuel_consumed:
            self.fuel_mass -= fuel_consumed
            self.total_mass -= fuel_consumed
        else:
            self.fuel_mass = 0
            self.total_mass = self.structure_mass + self.payload_mass

    def update_acceleration(self, thrust_x, thrust_y, thrust_z,
                            gravitational_acceleration_x, gravitational_acceleration_y, gravitational_acceleration_z):
        self.acceleration_x = thrust_x / self.total_mass + gravitational_acceleration_x
        self.acceleration_y = thrust_y / self.total_mass + gravitational_acceleration_y
        self.acceleration_z = thrust_z / self.total_mass + gravitational_acceleration_z

    def update_velocity(self, time_step):
        self.velocity_x += self.acceleration_x * time_step
        self.velocity_y += self.acceleration_y * time_step
        self.velocity_z += self.acceleration_z * time_step

    def update_position(self, time_step):
        self.x += self.velocity_x * time_step
        self.y += self.velocity_y * time_step
        self.z += self.velocity_z * time_step

    def calculate_total_gravitational_acceleration(self, spaceship, bodies):
        total_x = 0
        total_y = 0
        total_z = 0
        for body_name, body_obj in bodies.items():
            acceleration_x, acceleration_y, acceleration_z = self.calculate_gravitational_acceleration_from_body(spaceship, body_obj)
            total_x += acceleration_x
            total_y += acceleration_y
            total_z += acceleration_z
        #print(total_x, total_y, total_z)
        return total_x, total_y, total_z

    def calculate_gravitational_acceleration_from_body(self, spaceship, body):
        x = body.x - spaceship.x
        y = body.y - spaceship.y
        z = body.z - spaceship.z
        distance_squared = x**2 + y**2 + z**2
        distance = sqrt(distance_squared)
        gravitational_acceleration = G * body.mass / distance_squared
        acceleration_x = gravitational_acceleration * x / distance
        acceleration_y = gravitational_acceleration * y / distance
        acceleration_z = gravitational_acceleration * z / distance
        print(f"{body.name}, distance={distance}, gravity_x={acceleration_x}, gravity_y={acceleration_y}, gravity_z={acceleration_z}")
        return acceleration_x, acceleration_y, acceleration_z

class PropulsionSystem():
    def __init__(self, max_thrust, specific_impulse, exhaust_velocity):
        self.max_thrust = max_thrust
        self.specific_impulse = specific_impulse
        self.exhaust_velocity = exhaust_velocity

    def calculate_thrust(self, throttle):
        if throttle >= 1.0:
            return self.max_thrust
        elif throttle <= 0.0:
            return 0
        else:
            return self.max_thrust * throttle

    def calculate_fuel_consumption(self, thrust_module, time_step):
        return thrust_module / self.exhaust_velocity / self.specific_impulse * time_step