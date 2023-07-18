import datetime
from settings import c, AVERAGE_RADIATION_ANGLE, AU, G
from math import pi, cos, sqrt

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
    x = body.x - spaceship.x
    y = body.y - spaceship.y
    z = body.z - spaceship.z
    distance_squared = x**2 + y**2 + z**2
    distance = sqrt(distance_squared)
    if distance<=body.radius:
        return 0, 0, 0
    gravitational_acceleration = G * body.mass / distance_squared
    acceleration_x = gravitational_acceleration * x / distance
    acceleration_y = gravitational_acceleration * y / distance
    acceleration_z = gravitational_acceleration * z / distance
    return acceleration_x, acceleration_y, acceleration_z

def simulate_spaceship_trajectory(self, start_time, input_vector):
    for i, iteration in enumerate(input_vector):
        throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step = iteration
        simulation_time = start_time + datetime.timedelta(minutes=i*time_step)
        self.timestamp = self.convert_to_julian_date(simulation_time)
        self.update_all_bodies_positions()
        self.spaceship.update_status(throttle=throttle,
                                     thrust_vector_x=thrust_vector_x,
                                     thrust_vector_y=thrust_vector_y,
                                     thrust_vector_z=thrust_vector_z,
                                     time_step=time_step,
                                     bodies=self.celestial_bodies)
    self.timestamp = self.convert_to_julian_date(start_time)
    self.update_all_bodies_positions()