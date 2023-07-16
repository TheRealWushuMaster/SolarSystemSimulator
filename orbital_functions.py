from settings import c, AVERAGE_RADIATION_ANGLE, AU
from math import pi, cos
from classes import Spaceship, PropulsionSystem

def calculate_radiation_pressure(luminosity, distance, reflectivity):
    return (1+reflectivity)*luminosity/4/pi/c * (cos(AVERAGE_RADIATION_ANGLE)*AU/distance)**2

def create_test_spaceship():
    return create_ship_without_takeoff(main_max_thrust=10000,
                                       main_specific_impulse=3000,
                                       main_exhaust_velocity=4500,
                                       ship_structure_mass=10000,
                                       ship_fuel_mass=5000,
                                       ship_payload_mass=2000,
                                       ship_radiation_reflectivity=0.5,
                                       ship_surface_area=0.01,
                                       ship_size=0.01)

def create_ship_with_takeoff(takeoff_max_thrust, takeoff_specific_impulse, takeoff_exhaust_velocity, takeoff_structure_mass, takeoff_fuel_mass,
                             main_max_thrust, main_specific_impulse, main_exhaust_velocity,
                             ship_structure_mass, ship_fuel_mass, ship_payload_mass, ship_radiation_reflectivity, ship_surface_area, ship_size):
    main_propulsion_system = PropulsionSystem(max_thrust=main_max_thrust,
                                              specific_impulse=main_specific_impulse,
                                              exhaust_velocity=main_exhaust_velocity)
    takeoff_propulsion_system = PropulsionSystem(max_thrust=takeoff_max_thrust,
                                                 specific_impulse=takeoff_specific_impulse,
                                                 exhaust_velocity=takeoff_exhaust_velocity,
                                                 structure_mass=takeoff_structure_mass,
                                                 fuel_mass=takeoff_fuel_mass)
    spaceship = Spaceship(structure_mass=ship_structure_mass,
                          fuel_mass=ship_fuel_mass,
                          payload_mass=ship_payload_mass,
                          main_propulsion_system=main_propulsion_system,
                          takeoff_propulsion_system=takeoff_propulsion_system,
                          radiation_reflectivity=ship_radiation_reflectivity,
                          surface_area=ship_surface_area,
                          size=ship_size,
                          takeoff_jettisoned=False)
    return spaceship

def create_ship_without_takeoff(main_max_thrust, main_specific_impulse, main_exhaust_velocity,
                                ship_structure_mass, ship_fuel_mass, ship_payload_mass, ship_radiation_reflectivity, ship_surface_area, ship_size):
    main_propulsion_system = PropulsionSystem(max_thrust=main_max_thrust,
                                              specific_impulse=main_specific_impulse,
                                              exhaust_velocity=main_exhaust_velocity)
    takeoff_propulsion_system = PropulsionSystem()
    spaceship = Spaceship(structure_mass=ship_structure_mass,
                          fuel_mass=ship_fuel_mass,
                          payload_mass=ship_payload_mass,
                          main_propulsion_system=main_propulsion_system,
                          takeoff_propulsion_system=takeoff_propulsion_system,
                          radiation_reflectivity=ship_radiation_reflectivity,
                          surface_area=ship_surface_area,
                          size=ship_size,
                          takeoff_jettisoned=True)
    return spaceship