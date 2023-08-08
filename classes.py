from math import sqrt, sin, cos, radians
from settings import G
from orbital_functions import calculate_total_gravitational_acceleration

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
                 main_propulsion_system, takeoff_propulsion_system,
                 radiation_reflectivity, surface_area,
                 x=0, y=0, z=0, velocity_x=0, velocity_y=0, velocity_z=0,
                 acceleration_x=0, acceleration_y=0, acceleration_z=0,
                 size=0.1, takeoff_jettisoned=False):
        self.x = x
        self.y = y
        self.z = z
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.velocity_z = velocity_z
        self.acceleration_x = acceleration_x
        self.acceleration_y = acceleration_y
        self.acceleration_z = acceleration_z
        self.total_mass = structure_mass + fuel_mass + payload_mass + takeoff_propulsion_system.structure_mass + takeoff_propulsion_system.fuel_mass
        self.structure_mass = structure_mass
        self.fuel_mass = fuel_mass
        self.payload_mass = payload_mass
        self.main_propulsion_system = main_propulsion_system
        self.takeoff_propulsion_system = takeoff_propulsion_system
        self.radiation_reflectivity = radiation_reflectivity
        self.surface_area = surface_area
        self.size = size
        self.takeoff_jettisoned = takeoff_jettisoned
        self.reset_values()
        self.gravitational_parameter = G * self.total_mass
    
    def reset_values(self):
        self.positions = []
        self.velocities = []
        self.accelerations = []
        self.thrust_vectors = []
        self.throttles = []
        self.fuel_masses = []
        self.takeoff_fuel_masses = []
        self.time_steps = []
        self.jettisons = []
        self.index = 0

    def update_status(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step, bodies):
        if self.takeoff_jettisoned:
            if self.fuel_mass > 0:
                thrust_module = self.main_propulsion_system.calculate_thrust(throttle)
            else:
                thrust_module = 0
        else:
            thrust_module = self.takeoff_propulsion_system.calculate_thrust(throttle)
        thrust_x = thrust_vector_x * thrust_module
        thrust_y = thrust_vector_y * thrust_module
        thrust_z = thrust_vector_z * thrust_module
        gravitational_acceleration_x, gravitational_acceleration_y, gravitational_acceleration_z = calculate_total_gravitational_acceleration(self, bodies)
        self.update_acceleration(thrust_x, thrust_y, thrust_z,
                                gravitational_acceleration_x, gravitational_acceleration_y, gravitational_acceleration_z)
        self.update_mass(thrust_module, time_step)
        self.update_velocity(time_step)
        self.update_position(time_step)
        self.store_values(throttle=throttle,
                        thrust_vector_x=thrust_vector_x,
                        thrust_vector_y=thrust_vector_y,
                        thrust_vector_z=thrust_vector_z,
                        time_step=time_step)
        self.index += 1

    def step_forward(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step, bodies):
        if self.index == len(self.positions):
            self.update_status(throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step, bodies)
        else:
            self.index += 1
            self.load_from_index()

    def step_backwards(self):
        if self.index > 0:
            self.index -= 1
        self.load_from_index()

    def load_from_index(self):
        self.x = self.positions[self.index-1][0]; self.y = self.positions[self.index-1][1]; self.z = self.positions[self.index-1][2]
        self.velocity_x = self.velocities[self.index-1][0]; self.velocity_y = self.velocities[self.index-1][1]; self.velocity_z = self.velocities[self.index-1][2]
        self.acceleration_x = self.accelerations[self.index-1][0]; self.acceleration_y = self.accelerations[self.index-1][1]; self.acceleration_z = self.accelerations[self.index-1][2]
        self.fuel_mass = self.fuel_masses[self.index-1]
        self.takeoff_propulsion_system.fuel_mass = self.takeoff_fuel_masses[self.index-1]
        self.takeoff_jettisoned = self.jettisons[self.index-1]

    def store_values(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step):
        self.positions.append((self.x, self.y, self.z))
        self.velocities.append((self.velocity_x, self.velocity_y, self.velocity_z))
        self.accelerations.append((self.acceleration_x, self.acceleration_y, self.acceleration_z))
        self.thrust_vectors.append((thrust_vector_x, thrust_vector_y, thrust_vector_z))
        self.throttles.append(throttle)
        self.fuel_masses.append(self.fuel_mass)
        self.takeoff_fuel_masses.append(self.takeoff_propulsion_system.fuel_mass)
        self.jettisons.append(self.takeoff_jettisoned)
        self.time_steps.append(time_step)

    def update_mass(self, thrust_module, time_step):
        if self.takeoff_jettisoned:
            fuel_consumed = self.main_propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
            if self.fuel_mass > fuel_consumed:
                self.fuel_mass -= fuel_consumed
            else:
                self.fuel_mass = 0
        else:
            fuel_consumed = self.takeoff_propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
            if self.takeoff.fuel_mass > fuel_consumed:
                self.takeoff_propulsion_system.fuel_mass -= fuel_consumed
            else:
                self.takeoff_jettisoned = True
                self.takeoff_propulsion_system.structure_mass = 0
                self.takeoff_propulsion_system.fuel_mass = 0
        self.total_mass = self.structure_mass + self.payload_mass + self.fuel_mass + self.takeoff_propulsion_system.structure_mass + self.takeoff_propulsion_system.fuel_mass
        self.gravitational_parameter = G * self.total_mass

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

    def attach_to_planet(self, planet_x, planet_y, planet_z, planet_velocity,
                         planet_mass, planet_radius, altitude, angle_deg=0,
                         eccentricity=0):
        distance_to_planet_center = planet_radius + altitude    # In kms
        angle_radians = radians(angle_deg)
        initial_x = planet_x + distance_to_planet_center * sin(angle_radians)
        initial_y = planet_y - distance_to_planet_center * cos(angle_radians)
        initial_z = planet_z
        semi_major_axis = distance_to_planet_center / sqrt(1 - eccentricity**2)
        orbital_velocity_module = sqrt(G * planet_mass * ((2 / distance_to_planet_center/1000) - (1 / semi_major_axis/1000))) / 1000    # In km/s
        orbital_velocity_x = orbital_velocity_module * cos(angle_radians)
        orbital_velocity_y = orbital_velocity_module * sin(angle_radians)
        velocity_x = planet_velocity[0] + orbital_velocity_x
        velocity_y = planet_velocity[1] + orbital_velocity_y
        velocity_z = planet_velocity[2]
        self.x, self.y, self.z = initial_x, initial_y, initial_z
        self.velocity_x, self.velocity_y, self.velocity_z = velocity_x, velocity_y, velocity_z

class PropulsionSystem():
    def __init__(self, max_thrust=0, specific_impulse=0, exhaust_velocity=0, structure_mass=0, fuel_mass=0):
        self.max_thrust = max_thrust
        self.specific_impulse = specific_impulse
        self.exhaust_velocity = exhaust_velocity
        self.structure_mass = structure_mass
        self.fuel_mass = fuel_mass

    def calculate_thrust(self, throttle):
        if throttle >= 1.0:
            return self.max_thrust / 1000
        elif throttle <= 0.0:
            return 0
        else:
            return self.max_thrust / 1000 * throttle    # Convert to distance in km

    def calculate_fuel_consumption(self, thrust_module, time_step):
        return thrust_module / (self.exhaust_velocity / 1000) / self.specific_impulse * time_step     # Convert exhaust velocity to km/s

class FlightPlan():
    def __init__(self):
        self.maneuvers = []
    
    def add_thrust_off_planet(self, duration, max_thrust, direction):
        # Add a maneuver to thrust off the planet with the specified parameters
        # duration: Time duration in seconds
        # max_thrust: Maximum thrust in Newtons
        # direction: Tuple representing the normalized thrust vector direction (x, y, z)
        pass

    def add_coast(self, duration):
        # Add a maneuver to coast without thrust for the specified duration
        # duration: Time duration in seconds
        pass

    def add_thrust_towards_planet(self, duration, max_thrust, planet_position):
        # Add a maneuver to thrust towards a planet with the specified parameters
        # duration: Time duration in seconds
        # max_thrust: Maximum thrust in Newtons
        # planet_position: Tuple representing the position of the target planet (x, y, z)
        pass

    def add_thrust_along_vector(self, duration, max_thrust, thrust_vector):
        # Add a maneuver to thrust along a specific vector with the specified parameters
        pass

    def add_speed_up(self, duration, acceleration):
        # Add a maneuver to speed up the spaceship by applying a constant acceleration
        pass

    def add_slow_down(self, duration, acceleration):
        # Add a maneuver to slow down the spaceship by applying a constant acceleration
        pass

    def calculate_thrust_vector(self, maneuver, spaceship_position, spaceship_velocity):
        # Calculate the thrust vector for a given maneuver based on the current state of the spaceship
        # maneuver: The maneuver for which to calculate the thrust vector
        # spaceship_position: Tuple representing the current position of the spaceship (x, y, z)
        # spaceship_velocity: Tuple representing the current velocity of the spaceship (vx, vy, vz)
        # Returns: Tuple representing the normalized thrust vector direction (x, y, z)
        pass

    def execute(self, spaceship):
        # Execute the flight plan by simulating the trajectory of the spaceship
        # spaceship: The spaceship object to simulate
        pass

    def populate_from_instructions(self, instructions):
        # Populate the flight plan from a list of high-level instructions
        pass

class Simulation():
    def __init__(self, start_time, end_time, default_time_step=60):
        self.start = start_time
        self.end = end_time
        self.default_time_step = default_time_step
        self.spaceships = {}

    def add_spaceship(self, spaceship_name, spaceship):
        if not spaceship_name in self.spaceships.items():
            self.spaceships[spaceship_name] = spaceship

    def remove_spaceship(self, spaceship_name):
        if spaceship_name in self.spaceships.items():
            del self.spaceships[spaceship_name]

    def run(self, time_step):
        pass

    def plot_trajectory(self):
        pass