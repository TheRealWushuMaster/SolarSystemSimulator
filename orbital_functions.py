from settings import G, c, AVERAGE_RADIATION_ANGLE, AU
from math import sqrt, pi, cos
from classes import Spaceship, PropulsionSystem

def calculate_radiation_pressure(luminosity, distance, reflectivity):
    return (1+reflectivity)*luminosity/4/pi/c * (cos(AVERAGE_RADIATION_ANGLE)*AU/distance)**2

def create_test_spaceship():
    test_propulsion_system = PropulsionSystem(max_thrust=5000000,
                                              specific_impulse=300,
                                              exhaust_velocity=3000)
    test_spaceship = Spaceship(structure_mass=5000,
                               fuel_mass=2000,
                               payload_mass=1000,
                               propulsion_system=test_propulsion_system,
                               radiation_reflectivity=0.5,
                               surface_area=0.01)
    return test_spaceship