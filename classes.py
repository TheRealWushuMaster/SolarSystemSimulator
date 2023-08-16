from datetime import datetime, timedelta
from copy import deepcopy
from settings import G, simulation_steps, DEFAULT_SMALL_TIME_STEP, DEFAULT_LARGE_TIME_STEP
from orbital_functions import calculate_total_gravitational_acceleration, vector_from_to, return_normalized_vector
from functions import convert_to_julian_date
from graphics import draw_celestial_bodies
from math import sin, cos, sqrt, radians

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

    def __str__(self):
        result = "Point\n"
        result += f"x = {self.x}, y = {self.y}, z = {self.z}"
        return result


class SpaceshipState():
    def __init__(self, x, y, z,
                 velocity_x, velocity_y, velocity_z,
                 acceleration_x, acceleration_y, acceleration_z):
        self.x = x
        self.y = y
        self.z = z
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.velocity_z = velocity_z
        self.acceleration_x = acceleration_x
        self.acceleration_y = acceleration_y
        self.acceleration_z = acceleration_z
    
    def __str__(self):
        result = "Spaceship state\n"
        result += f"x = {self.x}, y = {self.y}, z = {self.z}\n"
        result += f"Velocity x = {self.velocity_x}, Velocity y = {self.velocity_y}, Velocity z = {self.velocity_z}\n"
        result += f"Accel x = {self.acceleration_x}, Accel y = {self.acceleration_y}, Accel z = {self.acceleration_z}\n"
        result += "====="
        return result

def orbit_planet_state(planet_position, planet_velocity,
                       planet_mass, planet_radius, altitude, angle_deg=0,
                       eccentricity=0):
    distance_to_planet_center = planet_radius + altitude    # In kms
    angle_radians = radians(angle_deg)
    x = planet_position.x + distance_to_planet_center * sin(angle_radians)
    y = planet_position.y - distance_to_planet_center * cos(angle_radians)
    z = planet_position.z
    semi_major_axis = distance_to_planet_center / sqrt(1 - eccentricity**2)
    orbital_velocity_module = sqrt(G * planet_mass * ((2 / distance_to_planet_center/1000) - (1 / semi_major_axis/1000))) / 1000    # In km/s
    orbital_velocity_x = orbital_velocity_module * cos(angle_radians)
    orbital_velocity_y = orbital_velocity_module * sin(angle_radians)
    velocity_x = planet_velocity.x + orbital_velocity_x
    velocity_y = planet_velocity.y + orbital_velocity_y
    velocity_z = planet_velocity.z
    state = SpaceshipState(x=x, y=y, z=z,
                           velocity_x=velocity_x, velocity_y=velocity_y, velocity_z=velocity_z,
                           acceleration_x=0, acceleration_y=0, acceleration_z=0)
    return state


class Spaceship():
    def __init__(self, structure_mass, fuel_mass, payload_mass,
                 main_propulsion_system, takeoff_propulsion_system,
                 takeoff_fuel_mass, radiation_reflectivity, surface_area,
                 initial_state, takeoff_jettisoned, size=0.1, flight_plan=None):
        self.reset_values()
        self.x = initial_state.x
        self.y = initial_state.y
        self.z = initial_state.z
        self.velocity_x = initial_state.velocity_x
        self.velocity_y = initial_state.velocity_y
        self.velocity_z = initial_state.velocity_z
        self.acceleration_x = initial_state.acceleration_x
        self.acceleration_y = initial_state.acceleration_y
        self.acceleration_z = initial_state.acceleration_z
        self.takeoff_jettisoned = takeoff_jettisoned
        self.fuel_mass = fuel_mass
        self.takeoff_fuel_mass = takeoff_fuel_mass
        self.structure_mass = structure_mass
        self.payload_mass = payload_mass
        self.total_mass = self.calculate_total_mass()
        self.store_initial_state(initial_state)
        self.index = 1
        if isinstance(main_propulsion_system, PropulsionSystem):
            self.main_propulsion_system = main_propulsion_system
        else:
            raise ValueError("Must provide a valid `PropulsionSystem` object.")
        if isinstance(takeoff_propulsion_system, PropulsionSystem):
            self.takeoff_propulsion_system = takeoff_propulsion_system
        else:
            self.takeoff_propulsion_system = PropulsionSystem()
        self.radiation_reflectivity = radiation_reflectivity
        self.surface_area = surface_area
        self.size = size
        if flight_plan is not None:
            self.flight_plan = flight_plan
        else:
            self.flight_plan = FlightPlan()
    
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

    def update_status(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z,
                      time_step, bodies, store_values=True):
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
        if store_values:
            self.store_values(throttle=throttle,
                            thrust_vector_x=thrust_vector_x,
                            thrust_vector_y=thrust_vector_y,
                            thrust_vector_z=thrust_vector_z,
                            time_step=time_step)
        self.index += 1

    def step_forward(self, time_step, bodies):
        if self.index == len(self.positions):
            self.execute_instruction(bodies, time_step)
        else:
            self.index += 1
            self.load_from_index()

    def step_backwards(self):
        if self.index > 1:
            self.index -= 1
        self.load_from_index()

    def load_from_index(self):
        self.x = self.positions[self.index-1].x
        self.y = self.positions[self.index-1].y
        self.z = self.positions[self.index-1].z
        self.velocity_x = self.velocities[self.index-1].x
        self.velocity_y = self.velocities[self.index-1].y
        self.velocity_z = self.velocities[self.index-1].z
        self.acceleration_x = self.accelerations[self.index-1].x
        self.acceleration_y = self.accelerations[self.index-1].y
        self.acceleration_z = self.accelerations[self.index-1].z
        self.fuel_mass = self.fuel_masses[self.index-1]
        self.takeoff_fuel_mass = self.takeoff_fuel_masses[self.index-1]
        self.takeoff_jettisoned = self.jettisons[self.index-1]

    def store_values(self, throttle, thrust_vector_x, thrust_vector_y, thrust_vector_z, time_step):
        self.positions.append(Point(self.x, self.y, self.z))
        self.velocities.append(Point(self.velocity_x, self.velocity_y, self.velocity_z))
        self.accelerations.append(Point(self.acceleration_x, self.acceleration_y, self.acceleration_z))
        self.thrust_vectors.append(Point(thrust_vector_x, thrust_vector_y, thrust_vector_z))
        self.throttles.append(throttle)
        self.fuel_masses.append(self.fuel_mass)
        self.takeoff_fuel_masses.append(self.takeoff_fuel_mass)
        self.jettisons.append(self.takeoff_jettisoned)
        self.time_steps.append(time_step)

    def store_initial_state(self, initial_state):
        self.positions.append(Point(initial_state.x, initial_state.y, initial_state.z))
        self.velocities.append(Point(initial_state.velocity_x, initial_state.velocity_y, initial_state.velocity_z))
        self.accelerations.append(Point(initial_state.acceleration_x, initial_state.acceleration_y, initial_state.acceleration_z))
        self.fuel_masses.append(self.fuel_mass)
        self.takeoff_fuel_masses.append(self.takeoff_fuel_mass)
        self.jettisons.append(self.takeoff_jettisoned)

    def update_mass(self, thrust_module, time_step):
        if self.takeoff_jettisoned:
            fuel_consumed = self.main_propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
            if self.fuel_mass > fuel_consumed:
                self.fuel_mass -= fuel_consumed
            else:
                self.fuel_mass = 0
        else:
            fuel_consumed = self.takeoff_propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
            if self.takeoff_fuel_mass > fuel_consumed:
                self.takeoff_propulsion_system.fuel_mass -= fuel_consumed
            else:
                self.takeoff_jettisoned = True
                self.takeoff_propulsion_system.structure_mass = 0
                self.takeoff_propulsion_system.fuel_mass = 0
        self.total_mass = self.structure_mass + self.payload_mass + self.fuel_mass + self.takeoff_propulsion_system.structure_mass + self.takeoff_fuel_mass

    def calculate_total_mass(self):
        mass = self.structure_mass + self.payload_mass + self.fuel_mass
        if self.takeoff_jettisoned:
            return mass
        else:
            return mass + self.takeoff_propulsion_system.structure_mass + self.takeoff_fuel_mass

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

    def execute_instruction(self, bodies, time_step):
        instruction = self.flight_plan.return_current_instruction()
        bodies_copy = deepcopy(bodies)
        if instruction is not None:
            if instruction["Remainder"] > time_step:
                instruction["Remainder"] -= time_step
            elif instruction["Remainder"] == time_step:
                instruction["Remainder"] = 0
                if instruction["Action"] == "Thrust":
                    throttle = instruction["Throttle"]
                    duration = instruction["Duration"]
                    if instruction["Direction"] == "To":
                        body = instruction["Body"]
                        spaceship_vector = (self.x, self.y, self.z)
                        body_vector = (bodies_copy[body].x, bodies_copy[body].y, bodies_copy[body].z)
                        vector_x, vector_y, vector_z = vector_from_to(spaceship_vector,
                                                                      body_vector,
                                                                      normalized=True)
                        self.update_status(throttle=throttle, thrust_vector_x=vector_x, thrust_vector_y=vector_y,
                                           thrust_vector_z=vector_z, time_step=duration, bodies=bodies_copy,
                                           store_values=True)
                    elif instruction["Direction"] == "Off":
                        body = instruction["Body"]
                        spaceship_vector = (self.x, self.y, self.z)
                        body_vector = (bodies_copy[body].x, bodies_copy[body].y, bodies_copy[body].z)
                        vector_x, vector_y, vector_z = vector_from_to(body_vector,
                                                                      spaceship_vector,
                                                                      normalized=True)
                        self.update_status(throttle=throttle, thrust_vector_x=vector_x, thrust_vector_y=vector_y,
                                           thrust_vector_z=vector_z, time_step=duration, bodies=bodies_copy,
                                           store_values=True)
                    elif instruction["Direction"] == "Vector":
                        vector_x = instruction["Vector"][0]
                        vector_y = instruction["Vector"][1]
                        vector_z = instruction["Vector"][2]
                        vector = return_normalized_vector(vector_x, vector_y, vector_z)
                        self.update_status(throttle=throttle, thrust_vector_x=vector[0],
                                           thrust_vector_y=vector[1], thrust_vector_z=vector[2],
                                           time_step=duration, bodies=bodies_copy, store_values=True)
                    else:
                        raise ValueError(f"Instruction direction '{instruction['Direction']}' not recognized.")
                elif instruction["Action"] == "Coast":
                    duration = instruction["Duration"]
                    self.update_status(throttle=0, thrust_vector_x=0, thrust_vector_y=0,
                                       thrust_vector_z=0, time_step=duration, bodies=bodies_copy,
                                       store_values=True)
                elif instruction["Action"] == "Speed up":
                    throttle = instruction["Throttle"]
                    duration = instruction["Duration"]
                    vector_x = self.velocity_x
                    vector_y = self.velocity_y
                    vector_z = self.velocity_z
                    vector = return_normalized_vector(vector_x, vector_y, vector_z)
                    self.update_status(throttle=throttle, thrust_vector_x=vector[0],
                                       thrust_vector_y=vector[1], thrust_vector_z=vector[2],
                                       time_step=duration, bodies=bodies_copy, store_values=True)
                elif instruction["Action"] == "Slow down":
                    throttle = instruction["Throttle"]
                    duration = instruction["Duration"]
                    vector_x = -self.velocity_x
                    vector_y = -self.velocity_y
                    vector_z = -self.velocity_z
                    vector = return_normalized_vector(vector_x, vector_y, vector_z)
                    self.update_status(throttle=throttle, thrust_vector_x=vector[0],
                                       thrust_vector_y=vector[1], thrust_vector_z=vector[2],
                                       time_step=duration, bodies=bodies_copy, store_values=True)
                else:
                    raise ValueError(f"Instruction action '{instruction['Action']}' not recognized.")
                #self.flight_plan.next_instruction()
            else:
                #remaining_time_step = time_step - instruction["Remainder"]
                #instruction["Remainder"] = 0
                self.flight_plan.next_instruction()
                # Decide how to apply the `remaining_time_step` on the next instruction
        else:
            # The ship will coast indefinitely
            self.update_status(throttle=0, thrust_vector_x=0, thrust_vector_y=0,
                               thrust_vector_z=0, time_step=time_step,
                               bodies=bodies_copy, store_values=True)
        self.flight_plan.next_instruction()


class PropulsionSystem():
    def __init__(self, max_thrust=0, specific_impulse=0,
                 exhaust_velocity=0, structure_mass=0):
        self.max_thrust = max_thrust
        self.specific_impulse = specific_impulse
        self.exhaust_velocity = exhaust_velocity
        self.structure_mass = structure_mass

    def calculate_thrust(self, throttle):
        if throttle >= 1.0:
            return self.max_thrust / 1000
        elif throttle <= 0.0:
            return 0
        else:
            return self.max_thrust / 1000 * throttle    # Convert to distance in km

    def calculate_fuel_consumption(self, thrust_module, time_step):
        # Need to verify this. It has units of kg if the exhaust velocity is in m/s.       
        return thrust_module/(self.exhaust_velocity/1000)*time_step  # Convert exhaust velocity to km/s


class FlightPlan():
    def __init__(self):
        self.instructions = []
        self.current_step = 0

    def add_coast(self, duration=DEFAULT_LARGE_TIME_STEP):
        self.instructions.append({"Action": "Coast",
                                  "Duration": duration,
                                  "Remainder": duration})

    def add_thrust_towards_body(self, throttle, body, duration=DEFAULT_SMALL_TIME_STEP):
        self.instructions.append({"Action": "Thrust",
                                  "Direction": "To",
                                  "Body": body,
                                  "Throttle": throttle,
                                  "Duration": duration,
                                  "Remainder": duration})

    def add_thrust_off_body(self, throttle, body, duration=DEFAULT_SMALL_TIME_STEP):
        self.instructions.append({"Action": "Thrust",
                                  "Direction": "Off",
                                  "Body": body,
                                  "Throttle": throttle,
                                  "Duration": duration,
                                  "Remainder": duration})

    def add_thrust_along_vector(self, throttle, vector, duration=DEFAULT_SMALL_TIME_STEP):
        self.instructions.append({"Action": "Thrust",
                                  "Direction": "Vector",
                                  "Vector": vector,
                                  "Throttle": throttle,
                                  "Duration": duration,
                                  "Remainder": duration})

    def add_speed_up(self, throttle, duration=DEFAULT_SMALL_TIME_STEP):
        self.instructions.append({"Action": "Speed up",
                                  "Throttle": throttle,
                                  "Duration": duration,
                                  "Remainder": duration})

    def add_slow_down(self, throttle, duration=DEFAULT_SMALL_TIME_STEP):
        self.instructions.append({"Action": "Slow down",
                                  "Throttle": throttle,
                                  "Duration": duration,
                                  "Remainder": duration})

    def reset_instructions(self):
        self.instructions = []

    def return_current_instruction(self):
        if self.current_step < len(self.instructions):
            return self.instructions[self.current_step]
        else:
            return None  # `None` must be interpreted as an indefinite "Coast"

    def next_instruction(self):
        if self.current_step < len(self.instructions):
            self.current_step += 1

    def populate_from_instructions(self, instructions):
        # Populate the flight plan from a list of high-level instructions
        pass


class Simulation():
    def __init__(self, date=None, start_time=None, end_time=None,
                 small_time_step=DEFAULT_SMALL_TIME_STEP,
                 large_time_step=DEFAULT_LARGE_TIME_STEP):
        if date==None:
            self.date = datetime.now()
        else:
            self.date = date
        if start_time == "now":
            self.start_time = self.date
        else:
            self.start_time = start_time
        self.end_time = end_time
        self.small_time_step = small_time_step
        self.large_time_step = large_time_step
        self.spaceships = {}
        self.time_steps = []
        self.user_time_step_index = 0
        self.user_time_step = simulation_steps[0][1]
        self.user_time_step_name = simulation_steps[0][0]
        self.auto_play = False
        self.frame_updates =[]
        self.timestamp = convert_to_julian_date(self.date)

    def step_date(self, app, up_or_down, time_step=None):
        if time_step==None:
            time_step = self.user_time_step
        time_step_delta = timedelta(seconds=time_step)
        if up_or_down=="up":
            if self.end_time is not None:
                new_date = self.date + time_step_delta
                if new_date > self.end_time:
                    self.date = self.end_time
                else:
                    self.date = new_date
            else:
                self.date += time_step_delta
        elif up_or_down=="down":
            if self.start_time is not None:
                new_date = self.date - time_step_delta
                if new_date < self.start_time:
                    self.date = self.start_time
                else:
                    self.date = new_date
            else:
                self.date -= time_step_delta
        else:
            raise ValueError(f"Argument '{up_or_down}' not recognized. Use 'up' or 'down'.")
        self.timestamp = convert_to_julian_date(self.date)
        self.update_simulation(up_or_down, time_step, app)

    def simulate_spaceships(self, app, up_or_down, time_step=None):
        if time_step is None:
            time_step = self.user_time_step
        if self.have_spaceships():
            for spaceship_name, spaceship in self.spaceships.items():
                if up_or_down == "up":
                    spaceship.step_forward(time_step, app.celestial_bodies)
                else:
                    spaceship.step_backwards()

    def update_simulation(self, up_or_down, time_step, app):
        self.simulate_spaceships(app, up_or_down, time_step)
        app.update_time_text()
        if isinstance(app.following, Spaceship):
            app.update_spaceship_text(spaceship_name=app.simulation.return_spaceship_name(app.following),
                                       spaceship=app.following)
        last_positions = app.save_positions()
        app.update_all_bodies_positions()
        position_changes = app.calculate_change_vectors(last_positions)
        app.update_orbits(position_changes)
        draw_celestial_bodies(app)

    def have_spaceships(self):
        return (len(self.spaceships)>0)

    def return_spaceship_name(self, spaceship):
        for spaceship_name, spaceship_object in self.spaceships.items():
            if spaceship_object == spaceship:
                return spaceship_name
        return None

    def adjust_user_time_step(self, up_or_down):
        if up_or_down == "up":
            if self.user_time_step_index < len(simulation_steps) - 1:
                self.user_time_step_index += 1
        elif up_or_down == "down":
            if self.user_time_step_index > 0:
                self.user_time_step_index -= 1
        else:
            raise ValueError(f"Argument '{up_or_down}' not recognized. Use 'up' or 'down'.")
        self.user_time_step_name = simulation_steps[self.user_time_step_index][0]
        self.user_time_step = simulation_steps[self.user_time_step_index][1]
    
    def add_spaceship(self, spaceship_name, spaceship):
        if not spaceship_name in self.spaceships.items():
            if isinstance(spaceship, Spaceship):
                self.spaceships[spaceship_name] = spaceship

    def remove_spaceship(self, spaceship_name):
        if spaceship_name in self.spaceships.items():
            del self.spaceships[spaceship_name]

    def run(self, time_step):
        pass

    def plot_trajectory(self):
        pass