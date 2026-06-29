from __future__ import annotations

from datetime import datetime, timedelta
from copy import deepcopy
from typing import TYPE_CHECKING, Any
from settings import simulation_steps, DEFAULT_SMALL_TIME_STEP, \
    DEFAULT_LARGE_TIME_STEP, DEFAULT_ORBIT_DIRECTION
from orbital_functions import calculate_total_gravitational_acceleration, vector_from_to, \
    return_normalized_vector, delta_v_to_establish_orbit
from functions import convert_to_julian_date, generate_spaceship_trajectory_color
from graphics import draw_celestial_bodies, draw_spaceship_trajectory
from math import sin, cos, radians, exp, log

if TYPE_CHECKING:
    from GUI import App


class Star:
    def __init__(self, NAME: str, X: float, Y: float, Z: float,
                 RADIUS: float, MASS: float, TEMPERATURE: float,
                 STAR_TYPE: str, LUMINOSITY: float,
                 ROTATION_PERIOD: float, ROTATION_VELOCITY: float,
                 COLOR_INDEX: float, COLOR: str, CIRCUMFERENCE: float,
                 LOCATION_PATH: list[int], AVERAGE_ORBITAL_SPEED: float,
                 ORBITAL_PERIOD: float, ORBIT_POINTS: list,
                 TEXTURE: str | None = None,
                 PARENT_BODY: str | None = None,
                 RINGS: int = 0) -> None:
        self.name = NAME
        self.x = X
        self.y = Y
        self.z = Z
        self.velocity_x: float = 0
        self.velocity_y: float = 0
        self.velocity_z: float = 0
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

    def return_position_vector(self, normalized: bool = True, coefficient: float = 1) -> Point:
        if normalized:
            norm = return_normalized_vector(self.x, self.y, self.z)
            return Point(coefficient*norm[0], coefficient*norm[1], coefficient*norm[2])
        else:
            return Point(coefficient*self.x, coefficient*self.y, coefficient*self.z)

    def __str__(self) -> str:
        return (f"Star(name={self.name}\nx={self.x}\ny={self.y}\nz={self.z}\nradius={self.radius}\nmass={self.mass}\n"
                f"temperature={self.temperature}\nrotation_period={self.rotation_period}\nrotation_velocity={self.rotation_velocity}\n"
                f"color_index={self.color_index}\ncolor={self.color}\ncircumference={self.circumference}\ntexture={self.texture}\n"
                f"star_type={self.star_type}\nluminosity={self.luminosity}\nparent_body={self.parent_body})")


class Planet:
    def __init__(self, NAME: str, X: float, Y: float, Z: float,
                 RADIUS: float, MASS: float, TEMPERATURE: float,
                 PARENT_BODY: str | None, PLANET_TYPE: str,
                 LOCATION_PATH: list[int], ROTATION_VELOCITY: float,
                 ROTATION_PERIOD: float, COLOR: str, CIRCUMFERENCE: float,
                 AVERAGE_ORBITAL_SPEED: float, ORBITAL_PERIOD: float,
                 ORBIT_POINTS: list,
                 TEXTURE: str | None = None,
                 ATMOSPHERE: int | None = None,
                 SURFACE: int | None = None,
                 RINGS: int = 0) -> None:
        self.name = NAME
        self.x = X
        self.y = Y
        self.z = Z
        self.velocity_x: float = 0
        self.velocity_y: float = 0
        self.velocity_z: float = 0
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

    def return_position_vector(self, normalized: bool = True, coefficient: float = 1) -> Point:
        if normalized:
            norm = return_normalized_vector(self.x, self.y, self.z)
            return Point(coefficient*norm[0], coefficient*norm[1], coefficient*norm[2])
        else:
            return Point(coefficient*self.x, coefficient*self.y, coefficient*self.z)

    def __str__(self) -> str:
        return (f"Planet(name={self.name}\nx={self.x}\ny={self.y}\nz={self.z}\nradius={self.radius}\nmass={self.mass}\n"
                f"temperature={self.temperature}\nrotation_velocity={self.rotation_velocity}\nrotation_period={self.rotation_period}\n"
                f"color={self.color}\ncircumference={self.circumference}\ntexture={self.texture}\nparent_body={self.parent_body}\n"
                f"planet_type={self.planet_type}\natmosphere={self.atmosphere}\nsurface={self.surface}\nrings={self.rings})")


class Point:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other: Point) -> Point:
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y, self.z + other.z)
        else:
            raise ValueError("Can only add two Point instances together.")

    def __sub__(self, other: Point) -> Point:
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y, self.z - other.z)
        else:
            raise ValueError("Can only subtract two Point instances together.")

    def __str__(self) -> str:
        return f"x = {self.x}, y = {self.y}, z = {self.z}"


class SpaceshipState:
    def __init__(self, x: float, y: float, z: float,
                 velocity_x: float, velocity_y: float, velocity_z: float,
                 acceleration_x: float, acceleration_y: float, acceleration_z: float) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.velocity_z = velocity_z
        self.acceleration_x = acceleration_x
        self.acceleration_y = acceleration_y
        self.acceleration_z = acceleration_z

    @classmethod
    def orbit_planet_state(cls, body: Star | Planet, altitude: float,
                           direction: str = DEFAULT_ORBIT_DIRECTION,
                           angle_deg: float = 0,
                           eccentricity: float = 0) -> SpaceshipState:
        distance_to_planet_center = body.radius + altitude    # In kms
        angle_radians = radians(angle_deg)
        x = body.x + distance_to_planet_center * sin(angle_radians)
        y = body.y - distance_to_planet_center * cos(angle_radians)
        z = body.z
        delta_v_x, delta_v_y, delta_v_z = delta_v_to_establish_orbit(
            (x, y, z), (0, 0, 0), body, eccentricity, direction=direction
        )
        return cls(x=x, y=y, z=z,
                   velocity_x=delta_v_x,
                   velocity_y=delta_v_y,
                   velocity_z=delta_v_z,
                   acceleration_x=0, acceleration_y=0, acceleration_z=0)

    def __str__(self) -> str:
        result = "Spaceship state\n"
        result += f"x = {self.x}, y = {self.y}, z = {self.z}\n"
        result += f"Velocity x = {self.velocity_x}, Velocity y = {self.velocity_y}, Velocity z = {self.velocity_z}\n"
        result += f"Accel x = {self.acceleration_x}, Accel y = {self.acceleration_y}, Accel z = {self.acceleration_z}\n"
        result += "====="
        return result


class Spaceship:
    def __init__(self, structure_mass: float, fuel_mass: float, payload_mass: float,
                 main_propulsion_system: PropulsionSystem,
                 takeoff_propulsion_system: PropulsionSystem | Any,
                 takeoff_fuel_mass: float, radiation_reflectivity: float,
                 surface_area: float, initial_state: SpaceshipState,
                 takeoff_jettisoned: bool, size: float = 0.1,
                 flight_plan: FlightPlan | None = None) -> None:
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
        self.flight_plan = flight_plan if flight_plan is not None else FlightPlan()
        self.trajectory_color: str = "#000000"

    def reset_values(self) -> None:
        self.positions: list[Point] = []
        self.velocities: list[Point] = []
        self.accelerations: list[Point] = []
        self.thrust_vectors: list[Point] = []
        self.throttles: list[float] = []
        self.fuel_masses: list[float] = []
        self.takeoff_fuel_masses: list[float] = []
        self.time_steps: list[float] = []
        self.jettisons: list[bool] = []
        self.index = 0

    def update_status(self, throttle: float,
                      thrust_vector_x: float, thrust_vector_y: float, thrust_vector_z: float,
                      time_step: float, bodies: dict[str, Any],
                      store_values: bool = True) -> None:
        if self.takeoff_jettisoned:
            if self.fuel_mass > 0:
                thrust_module = self.main_propulsion_system.calculate_thrust(throttle)
            else:
                thrust_module = 0.0
        else:
            thrust_module = self.takeoff_propulsion_system.calculate_thrust(throttle)
        thrust_x = thrust_vector_x * thrust_module
        thrust_y = thrust_vector_y * thrust_module
        thrust_z = thrust_vector_z * thrust_module
        grav_x, grav_y, grav_z = calculate_total_gravitational_acceleration(self, bodies)
        self.update_acceleration(thrust_x, thrust_y, thrust_z, grav_x, grav_y, grav_z)
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

    def step_forward(self, time_step: float, bodies: dict[str, Any]) -> None:
        if self.index == len(self.positions):
            self.execute_instruction(bodies, time_step)
        else:
            self.index += 1
            self.load_from_index()

    def step_backwards(self) -> None:
        if self.index > 1:
            self.index -= 1
        self.load_from_index()

    def load_from_index(self) -> None:
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

    def store_values(self, throttle: float,
                     thrust_vector_x: float, thrust_vector_y: float, thrust_vector_z: float,
                     time_step: float) -> None:
        self.positions.append(Point(self.x, self.y, self.z))
        self.velocities.append(Point(self.velocity_x, self.velocity_y, self.velocity_z))
        self.accelerations.append(Point(self.acceleration_x, self.acceleration_y, self.acceleration_z))
        self.thrust_vectors.append(Point(thrust_vector_x, thrust_vector_y, thrust_vector_z))
        self.throttles.append(throttle)
        self.fuel_masses.append(self.fuel_mass)
        self.takeoff_fuel_masses.append(self.takeoff_fuel_mass)
        self.jettisons.append(self.takeoff_jettisoned)
        self.time_steps.append(time_step)

    def store_initial_state(self, initial_state: SpaceshipState) -> None:
        self.positions.append(Point(initial_state.x, initial_state.y, initial_state.z))
        self.velocities.append(Point(initial_state.velocity_x, initial_state.velocity_y, initial_state.velocity_z))
        self.accelerations.append(Point(initial_state.acceleration_x, initial_state.acceleration_y, initial_state.acceleration_z))
        self.fuel_masses.append(self.fuel_mass)
        self.takeoff_fuel_masses.append(self.takeoff_fuel_mass)
        self.jettisons.append(self.takeoff_jettisoned)

    def update_mass(self, thrust_module: float, time_step: float) -> None:
        if self.takeoff_jettisoned:
            fuel_consumed = self.main_propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
            if self.fuel_mass > fuel_consumed:
                self.fuel_mass -= fuel_consumed
            else:
                self.fuel_mass = 0.0
        else:
            fuel_consumed = self.takeoff_propulsion_system.calculate_fuel_consumption(thrust_module, time_step)
            if self.takeoff_fuel_mass > fuel_consumed:
                self.takeoff_propulsion_system.fuel_mass -= fuel_consumed
            else:
                self.takeoff_jettisoned = True
                self.takeoff_propulsion_system.structure_mass = 0
                self.takeoff_propulsion_system.fuel_mass = 0
        self.total_mass = (self.structure_mass + self.payload_mass + self.fuel_mass
                           + self.takeoff_propulsion_system.structure_mass + self.takeoff_fuel_mass)

    def calculate_total_mass(self) -> float:
        mass = self.structure_mass + self.payload_mass + self.fuel_mass
        if self.takeoff_jettisoned:
            return mass
        else:
            return mass + self.takeoff_propulsion_system.structure_mass + self.takeoff_fuel_mass

    def update_acceleration(self, thrust_x: float, thrust_y: float, thrust_z: float,
                            grav_x: float, grav_y: float, grav_z: float) -> None:
        self.acceleration_x = thrust_x / self.total_mass / 1000 + grav_x
        self.acceleration_y = thrust_y / self.total_mass / 1000 + grav_y
        self.acceleration_z = thrust_z / self.total_mass / 1000 + grav_z

    def update_velocity(self, time_step: float) -> None:
        self.velocity_x += self.acceleration_x * time_step
        self.velocity_y += self.acceleration_y * time_step
        self.velocity_z += self.acceleration_z * time_step

    def update_position(self, time_step: float) -> None:
        self.x += self.velocity_x * time_step
        self.y += self.velocity_y * time_step
        self.z += self.velocity_z * time_step

    def execute_instruction(self, bodies: dict[str, Any], time_step: float) -> None:
        instruction, instructions, index = self.flight_plan.return_current_instruction()
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
                        vector_x, vector_y, vector_z = vector_from_to(spaceship_vector, body_vector, normalized=True)
                        self.update_status(throttle=throttle, thrust_vector_x=vector_x, thrust_vector_y=vector_y,
                                           thrust_vector_z=vector_z, time_step=duration, bodies=bodies_copy,
                                           store_values=True)
                    elif instruction["Direction"] == "Off":
                        body = instruction["Body"]
                        spaceship_vector = (self.x, self.y, self.z)
                        body_vector = (bodies_copy[body].x, bodies_copy[body].y, bodies_copy[body].z)
                        vector_x, vector_y, vector_z = vector_from_to(body_vector, spaceship_vector, normalized=True)
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
                    vector = return_normalized_vector(self.velocity_x, self.velocity_y, self.velocity_z)
                    self.update_status(throttle=throttle, thrust_vector_x=vector[0],
                                       thrust_vector_y=vector[1], thrust_vector_z=vector[2],
                                       time_step=duration, bodies=bodies_copy, store_values=True)
                elif instruction["Action"] == "Slow down":
                    throttle = instruction["Throttle"]
                    duration = instruction["Duration"]
                    velocity = self.return_velocity_vector(normalized=True)
                    self.update_status(throttle=throttle, thrust_vector_x=velocity.x,
                                       thrust_vector_y=velocity.y, thrust_vector_z=velocity.z,
                                       time_step=duration, bodies=bodies_copy, store_values=True)
                elif instruction["Action"] == "Delta V":
                    delta_v = instruction["Amount"] * 1000  # Convert to m/s
                    reference = instruction["Reference"]
                    direction = 1 if delta_v > 0 else -1
                    delta_v = abs(delta_v)
                    duration = instruction["Duration"]
                    if self.takeoff_jettisoned:
                        v_exhaust = self.main_propulsion_system.exhaust_velocity
                        max_thrust = self.main_propulsion_system.max_thrust
                    else:
                        v_exhaust = self.takeoff_propulsion_system.exhaust_velocity
                        max_thrust = self.takeoff_propulsion_system.max_thrust
                    delta_m_max = max_thrust / v_exhaust * duration
                    delta_v_max = v_exhaust * log(self.total_mass / (self.total_mass - delta_m_max))
                    num_periods = delta_v / delta_v_max
                    velocity = self.return_velocity_vector(normalized=False, coefficient=direction)
                    thrust_x = velocity.x
                    thrust_y = velocity.y
                    thrust_z = velocity.z
                    if reference in bodies:
                        planet_velocity = (bodies[reference].velocity_x,
                                           bodies[reference].velocity_y,
                                           bodies[reference].velocity_z)
                        thrust_x -= planet_velocity[0]
                        thrust_y -= planet_velocity[1]
                        thrust_z -= planet_velocity[2]
                    thrust_x, thrust_y, thrust_z = return_normalized_vector(
                        x=thrust_x*direction, y=thrust_y*direction, z=thrust_z*direction
                    )
                    if num_periods <= 1:
                        throttle = self.total_mass * (1 - exp(-delta_v/v_exhaust)) * v_exhaust / max_thrust / duration
                        self.update_status(throttle=throttle, thrust_vector_x=thrust_x,
                                           thrust_vector_y=thrust_y, thrust_vector_z=thrust_z,
                                           time_step=duration, bodies=bodies_copy, store_values=True)
                    else:
                        whole = int(num_periods)
                        fract = num_periods - whole
                        instructions.pop(index)
                        for i in range(whole):
                            self.flight_plan.add_delta_v(delta_v=delta_v_max/1000*direction,
                                                         reference=reference,
                                                         duration=instruction["Duration"],
                                                         index=index+i)
                        if fract > 0:
                            self.flight_plan.add_delta_v(delta_v=delta_v_max/1000*fract*direction,
                                                         reference=reference,
                                                         duration=instruction["Duration"],
                                                         index=index+whole)
                        self.update_status(throttle=1, thrust_vector_x=thrust_x,
                                           thrust_vector_y=thrust_y, thrust_vector_z=thrust_z,
                                           time_step=duration, bodies=bodies_copy, store_values=True)
                elif instruction["Action"] == "Hohmann":
                    planet_name = instruction["Planet"]
                    new_altitude = instruction["Altitude"]
                    duration = instruction["Duration"]
                else:
                    raise ValueError(f"Instruction action '{instruction['Action']}' not recognized.")
            else:
                self.flight_plan.next_instruction()
                # Decide how to apply the `remaining_time_step` on the next instruction
        else:
            # The ship will coast indefinitely
            self.update_status(throttle=0, thrust_vector_x=0, thrust_vector_y=0,
                               thrust_vector_z=0, time_step=time_step,
                               bodies=bodies_copy, store_values=True)
        self.flight_plan.next_instruction()

    def return_position_vector(self, normalized: bool = False, coefficient: float = 1) -> Point:
        if normalized:
            norm = return_normalized_vector(self.x, self.y, self.z)
            return Point(coefficient*norm[0], coefficient*norm[1], coefficient*norm[2])
        else:
            return Point(coefficient*self.x, coefficient*self.y, coefficient*self.z)

    def return_velocity_vector(self, normalized: bool = False, coefficient: float = 1) -> Point:
        if normalized:
            norm = return_normalized_vector(self.velocity_x, self.velocity_y, self.velocity_z)
            return Point(coefficient*norm[0], coefficient*norm[1], coefficient*norm[2])
        else:
            return Point(coefficient*self.velocity_x, coefficient*self.velocity_y, coefficient*self.velocity_z)


class PropulsionSystem:
    def __init__(self, max_thrust: float = 0, specific_impulse: float = 0,
                 exhaust_velocity: float = 0, structure_mass: float = 0) -> None:
        self.max_thrust = max_thrust
        self.specific_impulse = specific_impulse
        self.exhaust_velocity = exhaust_velocity
        self.structure_mass = structure_mass

    def calculate_thrust(self, throttle: float) -> float:
        if throttle >= 1.0:
            return self.max_thrust
        elif throttle <= 0.0:
            return 0.0
        else:
            return self.max_thrust * throttle

    def calculate_fuel_consumption(self, thrust_module: float, time_step: float) -> float:
        return thrust_module / self.exhaust_velocity * time_step


class FlightPlan:
    def __init__(self) -> None:
        self.instructions: list[dict[str, Any]] = []
        self.current_step: int = 0

    def add_coast(self, duration: float = DEFAULT_LARGE_TIME_STEP) -> None:
        self.instructions.append({"Action": "Coast",
                                   "Duration": duration,
                                   "Remainder": duration})

    def store_instruction(self, instruction: dict[str, Any], index: int | None = None) -> None:
        if index is None:
            self.instructions.append(instruction)
        else:
            self.instructions.insert(index, instruction)

    def add_thrust_towards_body(self, throttle: float, body: str,
                                duration: float = DEFAULT_SMALL_TIME_STEP,
                                index: int | None = None) -> None:
        self.store_instruction({"Action": "Thrust", "Direction": "To", "Body": body,
                                "Throttle": throttle, "Duration": duration, "Remainder": duration}, index)

    def add_thrust_off_body(self, throttle: float, body: str,
                            duration: float = DEFAULT_SMALL_TIME_STEP,
                            index: int | None = None) -> None:
        self.store_instruction({"Action": "Thrust", "Direction": "Off", "Body": body,
                                "Throttle": throttle, "Duration": duration, "Remainder": duration}, index)

    def add_thrust_along_vector(self, throttle: float,
                                vector: tuple[float, float, float],
                                duration: float = DEFAULT_SMALL_TIME_STEP,
                                index: int | None = None) -> None:
        self.store_instruction({"Action": "Thrust", "Direction": "Vector", "Vector": vector,
                                "Throttle": throttle, "Duration": duration, "Remainder": duration}, index)

    def add_speed_up(self, throttle: float, duration: float = DEFAULT_SMALL_TIME_STEP,
                     index: int | None = None) -> None:
        self.store_instruction({"Action": "Speed up", "Throttle": throttle,
                                "Duration": duration, "Remainder": duration}, index)

    def add_slow_down(self, throttle: float, duration: float = DEFAULT_SMALL_TIME_STEP,
                      index: int | None = None) -> None:
        self.store_instruction({"Action": "Slow down", "Throttle": throttle,
                                "Duration": duration, "Remainder": duration}, index)

    def add_delta_v(self, delta_v: float, reference: str,
                    duration: float = DEFAULT_SMALL_TIME_STEP,
                    index: int | None = None) -> None:
        self.store_instruction({"Action": "Delta V", "Amount": delta_v, "Reference": reference,
                                "Duration": duration, "Remainder": duration}, index)

    def add_hohmann_transfer(self, planet_name: str, altitude: float,
                             duration: float = DEFAULT_SMALL_TIME_STEP,
                             index: int | None = None) -> None:
        self.store_instruction({"Action": "Hohmann", "Planet": planet_name, "Altitude": altitude,
                                "Duration": duration, "Remainder": duration}, index)

    def reset_instructions(self) -> None:
        self.instructions = []

    def return_current_instruction(self) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, int | None]:
        if self.current_step < len(self.instructions):
            return self.instructions[self.current_step], self.instructions, self.current_step
        else:
            return None, None, None  # `None` must be interpreted as an indefinite "Coast"

    def next_instruction(self) -> None:
        if self.current_step < len(self.instructions):
            self.current_step += 1


class Simulation:
    def __init__(self, gui: App,
                 date: datetime | None = None,
                 start_time: datetime | str | None = None,
                 end_time: datetime | None = None,
                 small_time_step: float = DEFAULT_SMALL_TIME_STEP,
                 large_time_step: float = DEFAULT_LARGE_TIME_STEP,
                 distance_reference_object: str = "Sun",
                 velocity_reference_object: str = "Sun",
                 following_object_name: str = "Sun",
                 celestial_bodies: dict[str, Star | Planet] | None = None) -> None:
        self.gui = gui
        self.date = date if date is not None else datetime.now()
        if start_time == "now":
            self.start_time: datetime | None = self.date
        else:
            self.start_time = start_time  # type: ignore[assignment]
        self.end_time = end_time
        self.small_time_step = small_time_step
        self.large_time_step = large_time_step
        self.spaceships: dict[str, Spaceship] = {}
        self.time_steps: list[float] = []
        self.user_time_step_index: int = 0
        self.user_time_step: float = simulation_steps[0][1]
        self.user_time_step_name: str = simulation_steps[0][0]
        self.auto_play: bool = False
        self.frame_updates: list = []
        self.timestamp: float = convert_to_julian_date(self.date)
        self.celestial_bodies: dict[str, Star | Planet] = celestial_bodies or {}
        self.distance_reference_object = distance_reference_object
        self.velocity_reference_object = velocity_reference_object
        self.update_velocity_reference()
        self.following_object_name = following_object_name
        self.update_following_object()

    def update_following_object(self, object_name: str | None = None) -> None:
        if object_name is None:
            object_name = self.following_object_name
        if object_name in self.celestial_bodies:
            self.following_object_name = object_name
            self.following_object: Star | Planet | Spaceship = self.celestial_bodies[object_name]
            self.origin = Point(self.following_object.x,
                                self.following_object.y,
                                self.following_object.z)
            self.gui.update_following_body_text(self.following_object_name, self.following_object)
        elif object_name in self.spaceships:
            self.following_object_name = object_name
            spaceship = self.spaceships[object_name]
            self.following_object = spaceship
            self.origin = Point(spaceship.x, spaceship.y, spaceship.z)
            self.gui.update_spaceship_text(object_name, spaceship)
        else:
            raise ValueError(f"Object '{object_name}' not found.")

    def update_velocity_reference(self) -> None:
        if self.velocity_reference_object in self.celestial_bodies:
            body = self.celestial_bodies[self.velocity_reference_object]
            self.velocity_reference = Point(body.velocity_x, body.velocity_y, body.velocity_z)
        elif self.velocity_reference_object in self.spaceships:
            ship = self.spaceships[self.velocity_reference_object]
            self.velocity_reference = Point(ship.velocity_x, ship.velocity_y, ship.velocity_z)
        else:
            raise ValueError(f"Object '{self.velocity_reference_object}' not found.")
        self.gui.widgets.canvas.itemconfigure(
            self.gui.velocity_reference_text,
            text=f"Velocity reference: {self.velocity_reference_object.upper()}"
        )

    def step_date(self, up_or_down: str, time_step: float | None = None) -> None:
        if time_step is None:
            time_step = self.user_time_step
        time_step_delta = timedelta(seconds=time_step)
        if up_or_down == "up":
            if self.end_time is not None:
                new_date = self.date + time_step_delta
                self.date = min(new_date, self.end_time)
            else:
                self.date += time_step_delta
        elif up_or_down == "down":
            if self.start_time is not None:
                new_date = self.date - time_step_delta
                self.date = max(new_date, self.start_time)
            else:
                self.date -= time_step_delta
        else:
            raise ValueError(f"Argument '{up_or_down}' not recognized. Use 'up' or 'down'.")
        self.timestamp = convert_to_julian_date(self.date)
        self.update_simulation(up_or_down, time_step)

    def simulate_spaceships(self, up_or_down: str, time_step: float | None = None) -> None:
        if time_step is None:
            time_step = self.user_time_step
        if self.have_spaceships():
            for spaceship_name, spaceship in self.spaceships.items():
                if up_or_down == "up":
                    spaceship.step_forward(time_step, self.celestial_bodies)
                else:
                    spaceship.step_backwards()

    def update_simulation(self, up_or_down: str, time_step: float) -> None:
        self.simulate_spaceships(up_or_down, time_step)
        self.gui.update_time_text()
        if isinstance(self.following_object, Spaceship):
            self.gui.update_spaceship_text(
                spaceship_name=self.return_spaceship_name(self.following_object),
                spaceship=self.following_object,
            )
        last_positions = self.gui.save_positions()
        self.gui.update_all_bodies_positions()
        self.update_following_object()
        position_changes = self.gui.calculate_change_vectors(last_positions)
        self.gui.update_orbits(position_changes)
        draw_celestial_bodies(self.gui)
        self.draw_spaceship_trajectories()
        self.update_velocity_reference()

    def have_spaceships(self) -> bool:
        return len(self.spaceships) > 0

    def return_spaceship_name(self, spaceship: Spaceship) -> str | None:
        for spaceship_name, spaceship_object in self.spaceships.items():
            if spaceship_object == spaceship:
                return spaceship_name
        return None

    def adjust_user_time_step(self, up_or_down: str) -> None:
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

    def add_spaceship(self, spaceship_name: str, spaceship: Spaceship) -> None:
        if spaceship_name not in self.spaceships:   # bug fix: was checking .items()
            if isinstance(spaceship, Spaceship):
                spaceship.trajectory_color = generate_spaceship_trajectory_color(spaceship_name)
                self.spaceships[spaceship_name] = spaceship

    def remove_spaceship(self, spaceship_name: str) -> None:
        if spaceship_name in self.spaceships:
            del self.spaceships[spaceship_name]

    def draw_spaceship_trajectories(self) -> None:
        for spaceship_name, spaceship in self.spaceships.items():
            draw_spaceship_trajectory(self.gui, spaceship.positions, spaceship.trajectory_color)
