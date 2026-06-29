"""
Typed flight-plan instructions.

Replaces the dict-based instructions in `classes.FlightPlan` and the
130-line if/elif chain in `Spaceship.execute_instruction`. The split of
responsibilities is:

  * Each `Instruction` answers one question per simulation step:
    "what throttle and thrust direction now?" (a `ThrustCommand`).
  * `FlightPlan` owns time bookkeeping: which instruction is active,
    how much of it remains, and advancing to the next one.
  * The spaceship (not this module) applies the physics.

Instructions never import the GUI or the spaceship class; they see the
ship only through the `ShipState` protocol, which makes them trivially
testable with a stub.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import exp, log
from typing import Protocol, cast, override

from core.physics import circular_orbit_velocity
from core.vec3 import Vec3


class ShipState(Protocol):
    """The minimal view of a spaceship that instructions need."""

    @property
    def position(self) -> Vec3: ...

    @property
    def velocity(self) -> Vec3: ...

    @property
    def total_mass(self) -> float: ...

    @property
    def exhaust_velocity(self) -> float:
        """Exhaust velocity of the currently active propulsion system, in m/s."""
        ...

    @property
    def max_thrust(self) -> float:
        """Maximum thrust of the currently active propulsion system, in N."""
        ...

    @property
    def reactionless(self) -> bool:
        """True for a cheat engine that thrusts without losing mass."""
        ...


class BodyState(Protocol):
    """The minimal view of a celestial body that instructions need."""

    @property
    def position(self) -> Vec3: ...

    @property
    def velocity(self) -> Vec3: ...


class GravitatingBodyState(BodyState, Protocol):
    """A body whose gravity an instruction reasons about (orbit insertion)."""

    @property
    def mass(self) -> float: ...

    @property
    def radius(self) -> float: ...


# ----------------------------------------------------------------------
# Rocket-equation throttle helpers (shared by burn instructions)
# ----------------------------------------------------------------------

def delta_v_for_throttle(ship: ShipState, throttle: float, dt: float) -> float:
    """Delta-v (m/s) delivered by burning at `throttle` for `dt` seconds."""
    if throttle <= 0.0 or ship.max_thrust <= 0.0:
        return 0.0
    mass: float = ship.total_mass
    # Reactionless: constant mass, so dv = F*throttle*dt / m (no rocket eq).
    if ship.reactionless:
        return ship.max_thrust * throttle * dt / mass
    if ship.exhaust_velocity <= 0.0:
        return 0.0
    v_e: float = ship.exhaust_velocity
    fuel_burned: float = ship.max_thrust * throttle * dt / v_e
    if fuel_burned >= mass:
        return float("inf")
    return v_e * log(mass / (mass - fuel_burned))


def throttle_for_delta_v(ship: ShipState, target_dv_m_s: float, dt: float) -> float:
    """
    Throttle in [0, 1] that delivers (about) `target_dv_m_s` over `dt`,
    found by inverting the rocket equation (or, for a reactionless engine,
    the plain F/m relation) and capped at full throttle.
    """
    if target_dv_m_s <= 0.0:
        return 0.0
    max_dv: float = delta_v_for_throttle(ship, 1.0, dt)
    if max_dv <= 0.0:
        return 0.0
    if target_dv_m_s >= max_dv:
        return 1.0
    mass: float = ship.total_mass
    if ship.reactionless:
        return target_dv_m_s * mass / (ship.max_thrust * dt)
    v_e: float = ship.exhaust_velocity
    fuel_needed: float = mass * (1.0 - exp(-target_dv_m_s / v_e))
    return fuel_needed * v_e / (ship.max_thrust * dt)


@dataclass(frozen=True)
class ThrustCommand:
    """What the engine should do for the current simulation step."""
    throttle: float = 0.0
    direction: Vec3 = field(default_factory=Vec3)

    @classmethod
    def coast(cls) -> ThrustCommand:
        return cls(throttle=0.0, direction=Vec3())


class Instruction(ABC):
    """
    Base class for all flight-plan instructions.

    An instruction is active for `duration` seconds of simulation time
    (except where noted, e.g. `DeltaVInstruction` completes when its
    delta-v has been delivered). `remaining` is decremented by the
    flight plan, never by the instruction itself.
    """

    def __init__(self, duration: float) -> None:
        if duration <= 0:
            raise ValueError("Instruction duration must be positive.")
        self.duration: float = duration
        self.remaining: float = duration

    @abstractmethod
    def command(self,
                ship: ShipState,
                bodies: dict[str, BodyState],
                dt: float) -> ThrustCommand:
        """Return the thrust command for a step of `dt` seconds."""

    def is_complete(self) -> bool:
        return self.remaining <= 0.0

    @override
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}("
                f"duration={self.duration:.6g}, remaining={self.remaining:.6g})")


class CoastInstruction(Instruction):
    """Coast (no thrust) for the given duration."""

    @override
    def command(self,
                ship: ShipState,
                bodies: dict[str, BodyState],
                dt: float) -> ThrustCommand:
        return ThrustCommand.coast()


class ThrustInstruction(Instruction):
    """
    Thrust at a fixed throttle for the given duration.

    The direction is resolved each step, so "towards Mars" keeps
    pointing at Mars as both bodies move:

      * `towards_body` / `away_from_body`: along the line between the
        ship and the named body.
      * `prograde` / `retrograde`: along / against the ship's current
        velocity vector.
      * `vector`: a fixed direction in the inertial frame.
    """

    def __init__(self,
                 throttle: float,
                 duration: float,
                 towards_body: str | None = None,
                 away_from_body: str | None = None,
                 prograde: bool = False,
                 retrograde: bool = False,
                 vector: Vec3 | None = None) -> None:
        super().__init__(duration)
        modes: list[bool] = [towards_body is not None,
                             away_from_body is not None,
                             prograde,
                             retrograde,
                             vector is not None]
        if sum(modes) != 1:
            raise ValueError("Specify exactly one direction mode: "
                             "towards_body, away_from_body, prograde, "
                             "retrograde or vector.")
        if not 0.0 < throttle <= 1.0:
            raise ValueError("Throttle must be in (0, 1].")
        self.throttle: float = throttle
        self.towards_body: str | None = towards_body
        self.away_from_body: str | None = away_from_body
        self.prograde: bool = prograde
        self.retrograde: bool = retrograde
        self.vector: Vec3 | None = vector.normalized() if vector is not None else None

    @override
    def command(self,
                ship: ShipState,
                bodies: dict[str, BodyState],
                dt: float) -> ThrustCommand:
        direction: Vec3 = self._resolve_direction(ship, bodies)
        return ThrustCommand(throttle=self.throttle, direction=direction)

    def _resolve_direction(self,
                           ship: ShipState,
                           bodies: dict[str, BodyState]) -> Vec3:
        if self.towards_body is not None:
            return (bodies[self.towards_body].position - ship.position).normalized()
        if self.away_from_body is not None:
            return (ship.position - bodies[self.away_from_body].position).normalized()
        if self.prograde:
            return ship.velocity.normalized()
        if self.retrograde:
            return -ship.velocity.normalized()
        assert self.vector is not None
        return self.vector


class DeltaVInstruction(Instruction):
    """
    Deliver a velocity change of `delta_v_km_s` (km/s), burning prograde
    for a positive value and retrograde for a negative one.

    If `reference_body` is given, prograde/retrograde are evaluated in
    that body's frame (ship velocity minus body velocity), which is what
    you want for orbital maneuvers around a planet.

    Unlike time-based instructions, this one completes when the delta-v
    has been delivered. `duration` acts as a time budget per the rocket
    equation: each step the throttle is sized to spread the remaining
    delta-v over the remaining time, capped at full throttle. If the
    engine cannot deliver the delta-v within the budget, the burn simply
    continues at full throttle until done.
    """

    def __init__(self,
                 delta_v_km_s: float,
                 duration: float,
                 reference_body: str | None = None) -> None:
        super().__init__(duration)
        if delta_v_km_s == 0:
            raise ValueError("Delta-v must be non-zero.")
        self.delta_v_km_s: float = delta_v_km_s
        self.reference_body: str | None = reference_body
        # Remaining delta-v to deliver, in m/s, always positive.
        self.delta_v_remaining: float = abs(delta_v_km_s) * 1000.0

    @override
    def is_complete(self) -> bool:
        return self.delta_v_remaining <= 0.0

    @override
    def command(self,
                ship: ShipState,
                bodies: dict[str, BodyState],
                dt: float) -> ThrustCommand:
        direction: Vec3 = self._burn_direction(ship, bodies)
        throttle: float = self._throttle_for_step(ship, dt)
        # Track delivery using the same rocket-equation estimate the
        # throttle was sized with.
        delivered: float = delta_v_for_throttle(ship, throttle, dt)
        self.delta_v_remaining = max(0.0, self.delta_v_remaining - delivered)
        return ThrustCommand(throttle=throttle, direction=direction)

    def _burn_direction(self,
                        ship: ShipState,
                        bodies: dict[str, BodyState]) -> Vec3:
        velocity: Vec3 = ship.velocity
        if self.reference_body is not None and self.reference_body in bodies:
            velocity = velocity - bodies[self.reference_body].velocity
        prograde: Vec3 = velocity.normalized()
        return prograde if self.delta_v_km_s > 0 else -prograde

    def _throttle_for_step(self, ship: ShipState, dt: float) -> float:
        """
        Size the throttle so the remaining delta-v is spread over the
        remaining time budget, capped at full throttle.
        """
        time_budget: float = max(self.remaining, dt)
        target_dv: float = self.delta_v_remaining * dt / time_budget
        return throttle_for_delta_v(ship, target_dv, dt)


class VectorBurnInstruction(Instruction):
    """
    Deliver a specific delta-v *vector* along a fixed inertial direction.

    Where `DeltaVInstruction` burns prograde/retrograde in a body's frame
    (a change of speed), this reproduces an arbitrary impulsive maneuver —
    such as a Lambert injection, whose required delta-v `v1 - v_origin`
    generally does not point along the craft's velocity. The direction is
    fixed in the inertial frame; the magnitude is delivered using the same
    rocket-equation throttle sizing as `DeltaVInstruction`, and the burn
    completes once the full delta-v has been applied.
    """

    def __init__(self, delta_v_vector_km_s: Vec3, duration: float) -> None:
        super().__init__(duration)
        magnitude: float = delta_v_vector_km_s.magnitude()
        if magnitude == 0.0:
            raise ValueError("Delta-v vector must be non-zero.")
        self.direction: Vec3 = delta_v_vector_km_s.normalized()
        self._initial_delta_v: float = magnitude * 1000.0      # m/s
        self.delta_v_remaining: float = self._initial_delta_v

    @override
    def is_complete(self) -> bool:
        return self.delta_v_remaining <= 0.0

    @override
    def command(self,
                ship: ShipState,
                bodies: dict[str, BodyState],
                dt: float) -> ThrustCommand:
        time_budget: float = max(self.remaining, dt)
        target_dv: float = self.delta_v_remaining * dt / time_budget
        throttle: float = throttle_for_delta_v(ship, target_dv, dt)
        delivered: float = delta_v_for_throttle(ship, throttle, dt)
        self.delta_v_remaining = max(0.0, self.delta_v_remaining - delivered)
        return ThrustCommand(throttle=throttle, direction=self.direction)


class OrbitInsertionInstruction(Instruction):
    """
    Reactive arrive-and-orbit: the default ending of a FLY_TO.

    The instruction stays dormant (coasting) until the ship comes within
    `capture_radius_km` of the target body, then burns to circularize the
    orbit at the *current* radius, in the ecliptic plane, preserving the
    ship's direction of travel around the body. It reads the live relative
    velocity each step and drives it towards the circular-orbit velocity,
    so the transfer does not need an exact 3D arrival state precomputed —
    it only has to deliver the ship near the planet, and real N-body
    gravity does the rest.

    Strategy (a reactive version of a real orbit-insertion burn):

      1. Coast (dormant) until within `capture_radius_km` of the target.
      2. Keep coasting while still falling toward periapsis (closing on
         the body) and safely above `target_altitude_km` — let gravity
         bring the craft down to its closest approach.
      3. At periapsis (where the velocity is purely tangential) brake
         retrograde down to the local circular speed. Braking there
         circularizes cleanly into a *low, stable* orbit, instead of the
         eccentric high orbit you get braking on the way in (whose large
         apoapsis the Sun's tide would unbind).

    It completes when the relative speed reaches circular (within
    `tolerance_km_s`) or the `max_delta_v_km_s` budget is spent; `timeout_s`
    is a safety net if the craft is never captured (e.g. the transfer
    missed), so the plan cannot hang on it forever.

    Simplification (documented): insertion is planar (the ecliptic z=0
    plane). Full 3D is future work.
    """

    DEFAULT_TIMEOUT_S: float = 5.0 * 365.25 * 86400.0  # 5 years

    def __init__(self,
                 target_body: str,
                 target_altitude_km: float,
                 capture_radius_km: float | None = None,
                 tolerance_km_s: float = 0.005,
                 max_delta_v_km_s: float = 6.0,
                 timeout_s: float | None = None) -> None:
        super().__init__(duration=timeout_s if timeout_s is not None else self.DEFAULT_TIMEOUT_S)
        self.target_body: str = target_body
        self.target_altitude_km: float = target_altitude_km
        self.capture_radius_km: float | None = capture_radius_km
        self.tolerance_km_s: float = tolerance_km_s
        self.max_delta_v_km_s: float = max_delta_v_km_s
        self._capturing: bool = False      # within the capture shell
        self._circularizing: bool = False  # reached periapsis, now braking
        self._inserted: bool = False
        self._delta_v_spent: float = 0.0   # km/s

    @override
    def is_complete(self) -> bool:
        # Circularized, gave up after spending the budget, or timed out.
        return self._inserted or self.remaining <= 0.0

    @override
    def command(self,
                ship: ShipState,
                bodies: dict[str, BodyState],
                dt: float) -> ThrustCommand:
        raw_body: BodyState | None = bodies.get(self.target_body)
        if raw_body is None:
            return ThrustCommand.coast()
        body: GravitatingBodyState = cast(GravitatingBodyState, raw_body)

        relative_position: Vec3 = ship.position - body.position
        radius: float = relative_position.magnitude()

        if not self._capturing:
            capture_radius: float = (self.capture_radius_km
                                     if self.capture_radius_km is not None
                                     else body.radius + self.target_altitude_km)
            if radius > capture_radius:
                return ThrustCommand.coast()   # not captured yet
            self._capturing = True             # latch: stay active even if we climb

        relative_velocity: Vec3 = ship.velocity - body.velocity

        # Coast down until the craft falls to the circularization altitude
        # (the centre-aimed approach would otherwise graze the surface).
        # Then circularize *there* — high enough that the burn integrates
        # cleanly and the resulting orbit sits well inside the SOI (stable
        # against the Sun's tide).
        if not self._circularizing:
            range_rate: float = relative_velocity.dot(relative_position.normalized())
            safe_radius: float = body.radius + self.target_altitude_km
            if range_rate < 0.0 and radius > safe_radius:
                return ThrustCommand.coast()
            self._circularizing = True

        # Drive the velocity toward the local circular-orbit velocity
        # (which nulls the radial component, so the periapsis is raised to
        # here rather than left grazing the surface). Brake-biased: never
        # fire while already slower than circular, so energy only falls and
        # the orbit cannot be boosted back out to escape.
        circular_speed: float = circular_orbit_velocity(body.mass, radius)
        error: Vec3 = self._circular_velocity_error(ship, body, relative_position, radius)
        if (error.magnitude() <= self.tolerance_km_s
                or self._delta_v_spent >= self.max_delta_v_km_s):
            self._inserted = True
            return ThrustCommand.coast()
        if relative_velocity.magnitude() <= circular_speed:
            return ThrustCommand.coast()

        throttle: float = throttle_for_delta_v(ship, error.magnitude() * 1000.0, dt)
        self._delta_v_spent += delta_v_for_throttle(ship, throttle, dt) / 1000.0
        return ThrustCommand(throttle=throttle, direction=error.normalized())

    def _circular_velocity_error(self,
                                 ship: ShipState,
                                 body: GravitatingBodyState,
                                 relative_position: Vec3,
                                 radius: float) -> Vec3:
        """Local circular-orbit velocity (inertial) minus the ship's velocity."""
        relative_velocity: Vec3 = ship.velocity - body.velocity
        radial_in_plane: Vec3 = Vec3(relative_position.x, relative_position.y, 0.0)
        if radial_in_plane.magnitude() == 0.0:
            radial_in_plane = Vec3(relative_velocity.x, relative_velocity.y, 0.0)
        radial_hat: Vec3 = radial_in_plane.normalized()
        tangential_ccw: Vec3 = Vec3(-radial_hat.y, radial_hat.x, 0.0)
        in_plane_velocity: Vec3 = Vec3(relative_velocity.x, relative_velocity.y, 0.0)
        sense: float = 1.0 if tangential_ccw.dot(in_plane_velocity) >= 0.0 else -1.0
        circular_speed: float = circular_orbit_velocity(body.mass, radius)
        desired_inertial: Vec3 = body.velocity + tangential_ccw * (sense * circular_speed)
        return desired_inertial - ship.velocity


class FlightPlan:
    """
    An ordered sequence of instructions plus the time bookkeeping to
    walk through them.

    The single entry point for the simulation loop is `next_command`:
    it returns the thrust command for the current step and advances the
    plan's internal clock. When all instructions are exhausted the plan
    returns a coast command forever.
    """

    def __init__(self, instructions: list[Instruction] | None = None) -> None:
        self.instructions: list[Instruction] = instructions if instructions is not None else []
        self.current_index: int = 0

    # ------------------------------------------------------------------
    # Builder helpers (chainable)
    # ------------------------------------------------------------------

    def add(self, instruction: Instruction, index: int | None = None) -> FlightPlan:
        if index is None:
            self.instructions.append(instruction)
        else:
            self.instructions.insert(index, instruction)
        return self

    def add_coast(self, duration: float) -> FlightPlan:
        return self.add(CoastInstruction(duration=duration))

    def add_thrust_towards_body(self, throttle: float, body: str,
                                duration: float) -> FlightPlan:
        return self.add(ThrustInstruction(throttle=throttle,
                                          duration=duration,
                                          towards_body=body))

    def add_thrust_away_from_body(self, throttle: float, body: str,
                                  duration: float) -> FlightPlan:
        return self.add(ThrustInstruction(throttle=throttle,
                                          duration=duration,
                                          away_from_body=body))

    def add_thrust_along_vector(self, throttle: float, vector: Vec3,
                                duration: float) -> FlightPlan:
        return self.add(ThrustInstruction(throttle=throttle,
                                          duration=duration,
                                          vector=vector))

    def add_speed_up(self, throttle: float, duration: float) -> FlightPlan:
        return self.add(ThrustInstruction(throttle=throttle,
                                          duration=duration,
                                          prograde=True))

    def add_slow_down(self, throttle: float, duration: float) -> FlightPlan:
        return self.add(ThrustInstruction(throttle=throttle,
                                          duration=duration,
                                          retrograde=True))

    def add_delta_v(self, delta_v_km_s: float, duration: float,
                    reference_body: str | None = None) -> FlightPlan:
        return self.add(DeltaVInstruction(delta_v_km_s=delta_v_km_s,
                                          duration=duration,
                                          reference_body=reference_body))

    def add_delta_v_vector(self, delta_v_vector_km_s: Vec3,
                           duration: float) -> FlightPlan:
        return self.add(VectorBurnInstruction(delta_v_vector_km_s=delta_v_vector_km_s,
                                              duration=duration))

    def add_orbit_insertion(self, body: str, target_altitude_km: float,
                            capture_radius_km: float | None = None,
                            tolerance_km_s: float = 0.005,
                            max_delta_v_km_s: float = 6.0) -> FlightPlan:
        return self.add(OrbitInsertionInstruction(target_body=body,
                                                  target_altitude_km=target_altitude_km,
                                                  capture_radius_km=capture_radius_km,
                                                  tolerance_km_s=tolerance_km_s,
                                                  max_delta_v_km_s=max_delta_v_km_s))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def current_instruction(self) -> Instruction | None:
        """The active instruction, or None when the plan is exhausted."""
        self._skip_completed()
        if self.current_index < len(self.instructions):
            return self.instructions[self.current_index]
        return None

    def next_command(self,
                     ship: ShipState,
                     bodies: dict[str, BodyState],
                     dt: float) -> ThrustCommand:
        """
        Return the thrust command for a simulation step of `dt` seconds
        and advance the plan clock. Coasts forever once exhausted.
        """
        instruction: Instruction | None = self.current_instruction()
        if instruction is None:
            return ThrustCommand.coast()
        command: ThrustCommand = instruction.command(ship, bodies, dt)
        instruction.remaining -= dt
        return command

    def is_complete(self) -> bool:
        self._skip_completed()
        return self.current_index >= len(self.instructions)

    def reset(self) -> None:
        """Rewind the plan so it can be executed again from the start."""
        self.current_index = 0
        for instruction in self.instructions:
            instruction.remaining = instruction.duration
            if isinstance(instruction, DeltaVInstruction):
                instruction.delta_v_remaining = abs(instruction.delta_v_km_s) * 1000.0
            elif isinstance(instruction, VectorBurnInstruction):
                instruction.delta_v_remaining = instruction._initial_delta_v
            elif isinstance(instruction, OrbitInsertionInstruction):
                instruction._capturing = False
                instruction._circularizing = False
                instruction._inserted = False
                instruction._delta_v_spent = 0.0

    def _skip_completed(self) -> None:
        while (self.current_index < len(self.instructions)
               and self.instructions[self.current_index].is_complete()):
            self.current_index += 1

    @override
    def __repr__(self) -> str:
        return (f"FlightPlan({len(self.instructions)} instructions, "
                f"current={self.current_index})")
