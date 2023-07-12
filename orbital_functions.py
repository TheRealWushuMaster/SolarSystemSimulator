from settings import G, c, AVERAGE_RADIATION_ANGLE, AU
from math import sqrt, pi, cos
from classes import Spaceship, PropulsionSystem

def calculate_total_gravitational_acceleration(spaceship, bodies):
    total_attraction_x = 0
    total_attraction_y = 0
    total_attraction_z = 0
    for body in bodies:
        total_x, total_y, total_z += calculate_gravitational_acceleration_from_body(spaceship, body)
    return total_x, total_y, total_z

def calculate_gravitational_acceleration_from_body(spaceship, body):
    dx = body.x - spaceship.x
    dy = body.y - spaceship.y
    dz = body.z - spaceship.z
    distance_squared = dx**2 + dy**2 + dz**2
    distance = sqrt(distance_squared)
    if distance == body.radius:
        return 0
    gravitational_acceleration = G * body.mass / distance_squared
    acceleration_x = gravitational_acceleration * dx / distance
    acceleration_y = gravitational_acceleration * dy / distance
    acceleration_z = gravitational_acceleration * dz / distance
    return acceleration_x, acceleration_y, acceleration_z

def calculate_radiation_pressure(luminosity, distance, reflectivity):
    return (1+reflectivity)*luminosity/4/pi/c * (cos(AVERAGE_RADIATION_ANGLE)*AU/distance)**2

def create_test_spaceship():
    propulsion_system = PropulsionSystem(max_thrust=50000,
                                         specific_impulse=300,
                                         exhaust_velocity=3000)
    test_spaceship = Spaceship(structure_mass=5000,
                               fuel_mass=2000,
                               payload_mass=1000,
                               propulsion_system=propulsion_system,
                               radiation_reflectivity=0.5,
                               surface_area=100)
    return test_spaceship