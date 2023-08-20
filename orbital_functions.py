import datetime
from settings import c, AVERAGE_RADIATION_ANGLE, AU, G
from math import pi, sin, cos, sqrt
from numpy import array, dot
from classes import Point

def calculate_radiation_pressure(luminosity, distance, reflectivity):
    return (1+reflectivity)*luminosity/4/pi/c * (cos(AVERAGE_RADIATION_ANGLE)*AU/distance)**2

def calculate_total_gravitational_acceleration(spaceship, bodies):
    total_x = 0
    total_y = 0
    total_z = 0
    for body_name, body_obj in bodies.items():
        acceleration_x, acceleration_y, acceleration_z = calculate_gravitational_acceleration_from_body(spaceship, body_obj)
        total_x += acceleration_x
        total_y += acceleration_y
        total_z += acceleration_z
    return total_x, total_y, total_z

def calculate_gravitational_acceleration_from_body(spaceship, body):
    x = (body.x - spaceship.x) * 1000   # Convert distances in km to meters
    y = (body.y - spaceship.y) * 1000
    z = (body.z - spaceship.z) * 1000
    distance_squared = x**2 + y**2 + z**2
    distance = sqrt(distance_squared)
    if distance<body.radius*1000:
        return 0, 0, 0
    gravitational_acceleration = G * body.mass / distance_squared / 1000    # Convert units from m/s^2 to km/s^2
    acceleration_x = gravitational_acceleration * x / distance
    acceleration_y = gravitational_acceleration * y / distance
    acceleration_z = gravitational_acceleration * z / distance
    return acceleration_x, acceleration_y, acceleration_z

def escape_velocity(body_mass, distance):
    return sqrt(2*G*body_mass/distance)

def orbital_velocity_module(planet_mass, distance, eccentricity=0):
    semi_major_axis = distance / sqrt(1 - eccentricity**2)
    orbital_velocity_module = sqrt(G * planet_mass * ((2 / distance/1000) - (1 / semi_major_axis/1000))) / 1000    # In km/s
    return orbital_velocity_module

def orbital_period(planet_mass, radius_or_semi_major_axis):
    return 2*pi*sqrt(radius_or_semi_major_axis**3/G/planet_mass)

def simulate_spaceship_trajectory(self, start_time, input_vector):
    for i, iteration in enumerate(input_vector):
        throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step = iteration
        simulation_time = start_time + datetime.timedelta(minutes=i*time_step)
        self.timestamp = self.convert_to_julian_date(simulation_time)
        self.update_all_bodies_positions(simulating=True)
        self.spaceship.update_status(throttle=throttle,
                                     thrust_vector_x=thrust_vector_x,
                                     thrust_vector_y=thrust_vector_y,
                                     thrust_vector_z=thrust_vector_z,
                                     time_step=time_step,
                                     bodies=self.celestial_bodies)
    self.timestamp = self.convert_to_julian_date(start_time)
    self.spaceship.x, self.spaceship.y, self.spaceship.z = self.spaceship.positions[0]

def hohmann_transfer(body, body_velocity, spaceship, r2):
    body_position = body.return_position_vector()
    spaceship_position = spaceship.return_positon_vector()
    initial_distance_vector = spaceship_position - body_position
    r1 = return_vector_module(initial_distance_vector.x,
                              initial_distance_vector.y,
                              initial_distance_vector.z)
    current_v1 = spaceship.return_velocity_vector() - body_velocity
    v1 = sqrt(G*body.mass/r2)
    v1_p = sqrt(2*G*body.mass*(1/r1 - 1/(r1+r2)))
    delta_v1 = v1_p - v1
    v2 = sqrt(G*body.mass/r2)
    v2_p = sqrt(2*G*body.mass*(1/r2 - 1/(r1+r2)))
    delta_v2 = v2 - v2_p
    transfer_time = orbital_period(body.mass, r1+r2)/2


def vector_from_to(base_vector, target_vector, normalized=False):
    target_vector_x, target_vector_y, target_vector_z = target_vector
    base_vector_x, base_vector_y, base_vector_z = base_vector
    vector_x = target_vector_x - base_vector_x
    vector_y = target_vector_y - base_vector_y
    vector_z = target_vector_z - base_vector_z
    if normalized:
        vector_x, vector_y, vector_z = return_normalized_vector(vector_x, vector_y, vector_z)
    return vector_x, vector_y, vector_z

def rotate_vector(vector, rotate_x=0, rotate_y=0, rotate_z=0, normalized=False):
    rotation_x = array([[1, 0, 0],
                           [0, cos(rotate_x), -sin(rotate_x)],
                           [0, sin(rotate_x), cos(rotate_x)]])
    rotation_y = array([[cos(rotate_y), 0, sin(rotate_y)],
                           [0, 1, 0],
                           [-sin(rotate_y), 0, cos(rotate_y)]])
    rotation_z = array([[cos(rotate_z), -sin(rotate_z), 0],
                           [sin(rotate_z), cos(rotate_z), 0],
                           [0, 0, 1]])
    rotated_vector = dot(rotation_z, dot(rotation_y, dot(rotation_x, vector)))
    if normalized:
        rotated_vector = return_normalized_vector(rotated_vector[0], rotated_vector[1], rotated_vector[2])
    return rotated_vector

def return_vector_module(x, y, z):
    return sqrt(x**2 + y**2 + z**2)

def return_normalized_vector(x, y, z):
    module = return_vector_module(x, y, z)
    return x/module, y/module, z/module