"""
Spaceship model.

Replaces the `Spaceship`, `SpaceshipState` and `PropulsionSystem`
classes in `classes.py`. The main differences:

  * One `StateSnapshot` history list instead of 9 parallel lists that
    had to stay index-aligned by hand.
  * The ship pulls its orders from `FlightPlan.next_command()`; the old
    130-line `execute_instruction` is gone.
  * Propulsion systems own their fuel, which fixes the old bug where
    `update_mass` decremented `takeoff_propulsion_system.fuel_mass`
    while everything else read `spaceship.takeoff_fuel_mass`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log
from typing import override

from core.flight_plan import FlightPlan, ThrustCommand
from core.integrator import Integrator, VelocityVerlet
from core.physics import GravitatingBody, gravitational_acceleration
from core.vec3 import Vec3

# Above this step length the motion is sub-stepped internally so the
# integrator never sees a step large enough to drift. The display can ask
# for a one-day or one-year jump; the physics is still advanced in chunks
# no longer than this. 60 s is comfortably accurate for Verlet even in low
# orbit; a future adaptive scheme can relax it during deep-space cruise.
DEFAULT_MAX_INTEGRATION_DT: float = 60.0  # s


@dataclass
class PropulsionSystem:
    """
    An engine plus its own fuel supply.

    A `reactionless` engine is a deliberate cheat: it produces thrust without
    burning any propellant, so its mass never changes and its delta-v is
    effectively unlimited. Not physical, but a fun "test drive" for flying
    any mission you like without worrying about the rocket equation.
    """
    max_thrust: float = 0.0          # N
    specific_impulse: float = 0.0    # s
    exhaust_velocity: float = 0.0    # m/s
    structure_mass: float = 0.0      # kg
    fuel_mass: float = 0.0           # kg
    reactionless: bool = False       # thrust without mass loss (a "test" drive)

    @property
    def has_fuel(self) -> bool:
        return self.reactionless or self.fuel_mass > 0.0

    def thrust(self, throttle: float) -> float:
        """Thrust (N) at the given throttle, clamped to [0, 1]."""
        return self.max_thrust * min(max(throttle, 0.0), 1.0)

    def fuel_needed(self, thrust: float, dt: float) -> float:
        """Fuel mass (kg) consumed by `thrust` newtons over `dt` seconds."""
        if self.reactionless or self.exhaust_velocity <= 0.0:
            return 0.0
        return thrust / self.exhaust_velocity * dt


@dataclass(frozen=True)
class StateSnapshot:
    """The complete dynamic state of a spaceship at one simulation step."""
    position: Vec3
    velocity: Vec3
    acceleration: Vec3
    thrust_direction: Vec3
    throttle: float
    main_fuel_mass: float
    takeoff_fuel_mass: float
    takeoff_jettisoned: bool
    time_step: float


class Spaceship:
    """
    A spacecraft with an optional two-stage propulsion setup.

    While `takeoff_jettisoned` is False the takeoff stage provides
    thrust and its structure and fuel count towards the total mass;
    when its fuel runs out, the stage is dropped automatically.

    The ship satisfies the `ShipState` protocol that flight-plan
    instructions consume.
    """

    def __init__(self,
                 structure_mass: float,
                 payload_mass: float,
                 main_propulsion: PropulsionSystem,
                 initial_position: Vec3,
                 initial_velocity: Vec3,
                 takeoff_propulsion: PropulsionSystem | None = None,
                 radiation_reflectivity: float = 0.5,
                 surface_area: float = 0.0,
                 size: float = 0.1,
                 flight_plan: FlightPlan | None = None,
                 integrator: Integrator | None = None,
                 max_integration_dt: float = DEFAULT_MAX_INTEGRATION_DT) -> None:
        self.structure_mass: float = structure_mass
        self.payload_mass: float = payload_mass
        self.main_propulsion: PropulsionSystem = main_propulsion
        self.takeoff_propulsion: PropulsionSystem | None = takeoff_propulsion
        self.takeoff_jettisoned: bool = takeoff_propulsion is None
        self.radiation_reflectivity: float = radiation_reflectivity
        self.surface_area: float = surface_area
        self.size: float = size
        self.flight_plan: FlightPlan = flight_plan if flight_plan is not None else FlightPlan()
        self.integrator: Integrator = integrator if integrator is not None else VelocityVerlet()
        self.max_integration_dt: float = max_integration_dt
        self.trajectory_color: str = "#000000"

        self._position: Vec3 = initial_position
        self._velocity: Vec3 = initial_velocity
        self._acceleration: Vec3 = Vec3()

        self.history: list[StateSnapshot] = [self._snapshot(command=ThrustCommand.coast(),
                                                            dt=0.0)]
        self.index: int = 0

    # ------------------------------------------------------------------
    # ShipState protocol
    # ------------------------------------------------------------------

    @property
    def position(self) -> Vec3:
        return self._position

    @property
    def velocity(self) -> Vec3:
        return self._velocity

    @property
    def acceleration(self) -> Vec3:
        return self._acceleration

    @property
    def total_mass(self) -> float:
        mass: float = (self.structure_mass + self.payload_mass
                       + self.main_propulsion.fuel_mass)
        if not self.takeoff_jettisoned and self.takeoff_propulsion is not None:
            mass += self.takeoff_propulsion.structure_mass + self.takeoff_propulsion.fuel_mass
        return mass

    @property
    def active_propulsion(self) -> PropulsionSystem:
        if not self.takeoff_jettisoned and self.takeoff_propulsion is not None:
            return self.takeoff_propulsion
        return self.main_propulsion

    @property
    def exhaust_velocity(self) -> float:
        return self.active_propulsion.exhaust_velocity

    @property
    def max_thrust(self) -> float:
        return self.active_propulsion.max_thrust

    @property
    def reactionless(self) -> bool:
        return self.active_propulsion.reactionless

    # ------------------------------------------------------------------
    # Simulation stepping
    # ------------------------------------------------------------------

    def step_forward(self, dt: float, bodies: dict[str, GravitatingBody]) -> None:
        """
        Advance one simulation step: replay from history when stepping
        over ground already covered, otherwise simulate a new step.
        """
        if self.index < len(self.history) - 1:
            self.index += 1
            self._restore(self.history[self.index])
        else:
            self._simulate_step(dt, bodies)

    def step_backwards(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._restore(self.history[self.index])

    def _simulate_step(self,
                       dt: float,
                       bodies: dict[str, GravitatingBody]) -> None:
        """
        Advance the dynamic state by `dt` and record one snapshot.

        The physics is sub-stepped so the integrator only ever sees a
        chunk no longer than `max_integration_dt`. The flight plan is
        queried *per sub-step*, so reactive instructions (orbit insertion)
        and short burns are resolved at sub-step resolution rather than
        being sampled once per (possibly day-long) display step. Fuel,
        mass and staging update per sub-step too, so a burn that empties a
        tank mid-step is handled correctly with the shrinking mass.
        """
        sub_dt, sub_steps = self._sub_step_plan(dt)
        command: ThrustCommand = ThrustCommand.coast()
        for _ in range(sub_steps):
            command = self.flight_plan.next_command(self, bodies, sub_dt)
            self._integrate_sub_step(command, sub_dt, bodies)

        self.history.append(self._snapshot(command=command, dt=dt))
        self.index += 1

    def _sub_step_plan(self, dt: float) -> tuple[float, int]:
        """Split `dt` into equal sub-steps no longer than the integration cap."""
        if dt <= self.max_integration_dt:
            return dt, 1
        count: int = ceil(dt / self.max_integration_dt)
        return dt / count, count

    def _integrate_sub_step(self,
                            command: ThrustCommand,
                            dt: float,
                            bodies: dict[str, GravitatingBody]) -> None:
        engine: PropulsionSystem = self.active_propulsion
        thrust: float = engine.thrust(command.throttle) if engine.has_fuel else 0.0
        fuel_needed: float = engine.fuel_needed(thrust, dt)
        if fuel_needed > engine.fuel_mass > 0.0:
            # Engine runs dry mid sub-step: scale thrust to the average
            # over the sub-step and burn what is left.
            thrust *= engine.fuel_mass / fuel_needed
            fuel_needed = engine.fuel_mass

        # Thrust acceleration (km/s^2), constant over the sub-step so the
        # integrator can treat the field (gravity + thrust) as a function of
        # position alone. A reactionless engine keeps constant mass, so it is
        # simply F/m; a real engine loses mass as it burns, so we convert the
        # exact rocket-equation delta-v to an acceleration — that stays
        # accurate even when a single sub-step spends a big fraction of the
        # mass (plain F/m at the start mass would under-deliver).
        thrust_acceleration: Vec3 = Vec3()
        if thrust > 0.0:
            mass_before: float = self.total_mass
            if engine.reactionless:
                delta_v_km_s: float = thrust / mass_before * dt / 1000.0
                thrust_acceleration = command.direction * (delta_v_km_s / dt)
            else:
                mass_after: float = mass_before - fuel_needed
                if mass_after > 0.0:
                    delta_v_km_s = engine.exhaust_velocity * log(mass_before / mass_after) / 1000.0
                    thrust_acceleration = command.direction * (delta_v_km_s / dt)

        def acceleration_at(position: Vec3) -> Vec3:
            return gravitational_acceleration(position, bodies) + thrust_acceleration

        self._position, self._velocity, self._acceleration = self.integrator.step(
            position=self._position,
            velocity=self._velocity,
            acceleration_at=acceleration_at,
            dt=dt)

        engine.fuel_mass -= fuel_needed
        if (not self.takeoff_jettisoned
                and self.takeoff_propulsion is not None
                and not self.takeoff_propulsion.has_fuel):
            self.takeoff_jettisoned = True

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _snapshot(self, command: ThrustCommand, dt: float) -> StateSnapshot:
        takeoff_fuel: float = (self.takeoff_propulsion.fuel_mass
                               if self.takeoff_propulsion is not None else 0.0)
        return StateSnapshot(position=self._position,
                             velocity=self._velocity,
                             acceleration=self._acceleration,
                             thrust_direction=command.direction,
                             throttle=command.throttle,
                             main_fuel_mass=self.main_propulsion.fuel_mass,
                             takeoff_fuel_mass=takeoff_fuel,
                             takeoff_jettisoned=self.takeoff_jettisoned,
                             time_step=dt)

    def _restore(self, snapshot: StateSnapshot) -> None:
        self._position = snapshot.position
        self._velocity = snapshot.velocity
        self._acceleration = snapshot.acceleration
        self.main_propulsion.fuel_mass = snapshot.main_fuel_mass
        if self.takeoff_propulsion is not None:
            self.takeoff_propulsion.fuel_mass = snapshot.takeoff_fuel_mass
        self.takeoff_jettisoned = snapshot.takeoff_jettisoned

    @property
    def trajectory(self) -> list[Vec3]:
        """Positions visited so far, for drawing."""
        return [snapshot.position for snapshot in self.history]

    @override
    def __repr__(self) -> str:
        return (f"Spaceship(position={self._position}, velocity={self._velocity}, "
                f"mass={self.total_mass:.6g} kg, step={self.index})")
