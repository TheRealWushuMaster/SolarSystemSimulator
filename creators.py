from classes import Star, Planet, Spaceship, SpaceshipState, PropulsionSystem, FlightPlan

def create_bodies(star_data=None, planet_data=None, moon_data=None):
    celestial_bodies = {}
    if star_data is not None:
        celestial_bodies.update(create_body_of_a_class(star_data, Star))
    if planet_data is not None:
        celestial_bodies.update(create_body_of_a_class(planet_data, Planet))
    if moon_data is not None:
        celestial_bodies.update(create_body_of_a_class(moon_data, Planet))
    return celestial_bodies

def create_body_of_a_class(body_data, body_class):
    bodies = {}
    for name, properties in body_data.items():
            body = body_class(name, **properties)
            bodies[name] = body
    return bodies

def create_iss(simulation):
    flight_plan = FlightPlan()
    earth = simulation.celestial_bodies["Earth"]
    initial_state = SpaceshipState.orbit_planet_state(body=earth, altitude=418)
    return create_ship_without_takeoff(main_max_thrust=0,
                                       main_specific_impulse=0,
                                       main_exhaust_velocity=1,
                                       ship_structure_mass=450000,
                                       ship_fuel_mass=0,
                                       ship_payload_mass=0,
                                       ship_radiation_reflectivity=0.5,
                                       ship_surface_area=0.009331,
                                       ship_size=0.109,
                                       flight_plan=flight_plan,
                                       initial_state=initial_state)

def create_test_spaceship(initial_state, flight_plan=None):
    if flight_plan is None:
        flight_plan = FlightPlan()
    return create_ship_without_takeoff(main_max_thrust=100000,
                                       main_specific_impulse=3000,
                                       main_exhaust_velocity=4500,
                                       ship_structure_mass=2000,
                                       ship_fuel_mass=4000,
                                       ship_payload_mass=500,
                                       ship_radiation_reflectivity=0.5,
                                       ship_surface_area=0.01,
                                       ship_size=0.01,
                                       flight_plan=flight_plan,
                                       initial_state=initial_state)

def create_ship_with_takeoff(takeoff_max_thrust, takeoff_specific_impulse, takeoff_exhaust_velocity,
                             takeoff_structure_mass, takeoff_fuel_mass, main_max_thrust, main_specific_impulse,
                             main_exhaust_velocity, ship_structure_mass, ship_fuel_mass, ship_payload_mass,
                             ship_radiation_reflectivity, ship_surface_area, ship_size, flight_plan, initial_state):
    main_propulsion_system = PropulsionSystem(max_thrust=main_max_thrust,
                                              specific_impulse=main_specific_impulse,
                                              exhaust_velocity=main_exhaust_velocity)
    takeoff_propulsion_system = PropulsionSystem(max_thrust=takeoff_max_thrust,
                                                 specific_impulse=takeoff_specific_impulse,
                                                 exhaust_velocity=takeoff_exhaust_velocity,
                                                 structure_mass=takeoff_structure_mass)
    spaceship = Spaceship(structure_mass=ship_structure_mass,
                          fuel_mass=ship_fuel_mass,
                          payload_mass=ship_payload_mass,
                          main_propulsion_system=main_propulsion_system,
                          takeoff_propulsion_system=takeoff_propulsion_system,
                          takeoff_fuel_mass=takeoff_fuel_mass,
                          radiation_reflectivity=ship_radiation_reflectivity,
                          surface_area=ship_surface_area,
                          size=ship_size,
                          takeoff_jettisoned=False,
                          flight_plan=flight_plan,
                          initial_state=initial_state)
    return spaceship

def create_ship_without_takeoff(main_max_thrust, main_specific_impulse, main_exhaust_velocity,
                                ship_structure_mass, ship_fuel_mass, ship_payload_mass,
                                ship_radiation_reflectivity, ship_surface_area, ship_size,
                                flight_plan, initial_state):
    main_propulsion_system = PropulsionSystem(max_thrust=main_max_thrust,
                                              specific_impulse=main_specific_impulse,
                                              exhaust_velocity=main_exhaust_velocity)
    takeoff_propulsion_system = PropulsionSystem()
    spaceship = Spaceship(structure_mass=ship_structure_mass,
                          fuel_mass=ship_fuel_mass,
                          payload_mass=ship_payload_mass,
                          main_propulsion_system=main_propulsion_system,
                          takeoff_propulsion_system=takeoff_propulsion_system,
                          takeoff_fuel_mass=0,
                          radiation_reflectivity=ship_radiation_reflectivity,
                          surface_area=ship_surface_area,
                          size=ship_size,
                          takeoff_jettisoned=True,
                          flight_plan=flight_plan,
                          initial_state=initial_state)
    return spaceship