from __future__ import annotations

from dataclasses import dataclass, field
from math import log

import pytest

from core.vec3 import Vec3
from core.flight_plan import (
    CoastInstruction,
    DeltaVInstruction,
    FlightPlan,
    ThrustCommand,
    ThrustInstruction,
)


@dataclass
class StubShip:
    """Minimal ShipState implementation for tests."""
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=lambda: Vec3(7.5, 0.0, 0.0))
    total_mass: float = 6500.0          # kg
    exhaust_velocity: float = 4500.0    # m/s
    max_thrust: float = 100000.0        # N
    reactionless: bool = False


@dataclass
class StubBody:
    """Minimal BodyState implementation for tests."""
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)


# ----------------------------------------------------------------------
# Instruction construction
# ----------------------------------------------------------------------

class TestInstructionValidation:
    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValueError):
            CoastInstruction(duration=-1.0)

    def test_zero_duration_rejected(self) -> None:
        with pytest.raises(ValueError):
            CoastInstruction(duration=0.0)

    def test_thrust_requires_exactly_one_direction_mode(self) -> None:
        with pytest.raises(ValueError):
            ThrustInstruction(throttle=0.5, duration=10.0)  # no mode
        with pytest.raises(ValueError):
            ThrustInstruction(throttle=0.5, duration=10.0,
                              prograde=True, retrograde=True)  # two modes

    def test_thrust_throttle_bounds(self) -> None:
        with pytest.raises(ValueError):
            ThrustInstruction(throttle=0.0, duration=10.0, prograde=True)
        with pytest.raises(ValueError):
            ThrustInstruction(throttle=1.5, duration=10.0, prograde=True)

    def test_delta_v_zero_rejected(self) -> None:
        with pytest.raises(ValueError):
            DeltaVInstruction(delta_v_km_s=0.0, duration=10.0)


# ----------------------------------------------------------------------
# Coast
# ----------------------------------------------------------------------

class TestCoast:
    def test_coast_returns_zero_throttle(self) -> None:
        ship = StubShip()
        instruction = CoastInstruction(duration=60.0)
        command: ThrustCommand = instruction.command(ship, {}, dt=10.0)
        assert command.throttle == 0.0


# ----------------------------------------------------------------------
# Thrust directions
# ----------------------------------------------------------------------

class TestThrustDirections:
    def test_towards_body_points_at_body(self) -> None:
        ship = StubShip(position=Vec3(0.0, 0.0, 0.0))
        mars = StubBody(position=Vec3(1000.0, 0.0, 0.0))
        instruction = ThrustInstruction(throttle=1.0, duration=10.0,
                                        towards_body="Mars")
        command = instruction.command(ship, {"Mars": mars}, dt=10.0)
        assert command.direction == Vec3(1.0, 0.0, 0.0)

    def test_away_from_body_points_away(self) -> None:
        ship = StubShip(position=Vec3(0.0, 0.0, 0.0))
        mars = StubBody(position=Vec3(1000.0, 0.0, 0.0))
        instruction = ThrustInstruction(throttle=1.0, duration=10.0,
                                        away_from_body="Mars")
        command = instruction.command(ship, {"Mars": mars}, dt=10.0)
        assert command.direction == Vec3(-1.0, 0.0, 0.0)

    def test_direction_tracks_moving_body(self) -> None:
        """'Towards Mars' must re-resolve as Mars moves."""
        ship = StubShip(position=Vec3(0.0, 0.0, 0.0))
        mars = StubBody(position=Vec3(1000.0, 0.0, 0.0))
        instruction = ThrustInstruction(throttle=1.0, duration=20.0,
                                        towards_body="Mars")
        first = instruction.command(ship, {"Mars": mars}, dt=10.0)
        mars.position = Vec3(0.0, 1000.0, 0.0)
        second = instruction.command(ship, {"Mars": mars}, dt=10.0)
        assert first.direction == Vec3(1.0, 0.0, 0.0)
        assert second.direction == Vec3(0.0, 1.0, 0.0)

    def test_prograde_follows_velocity(self) -> None:
        ship = StubShip(velocity=Vec3(0.0, 3.0, 4.0))
        instruction = ThrustInstruction(throttle=0.5, duration=10.0,
                                        prograde=True)
        command = instruction.command(ship, {}, dt=10.0)
        assert command.direction == Vec3(0.0, 0.6, 0.8)

    def test_retrograde_opposes_velocity(self) -> None:
        ship = StubShip(velocity=Vec3(0.0, 3.0, 4.0))
        instruction = ThrustInstruction(throttle=0.5, duration=10.0,
                                        retrograde=True)
        command = instruction.command(ship, {}, dt=10.0)
        assert command.direction == Vec3(0.0, -0.6, -0.8)

    def test_fixed_vector_is_normalized(self) -> None:
        instruction = ThrustInstruction(throttle=1.0, duration=10.0,
                                        vector=Vec3(10.0, 0.0, 0.0))
        command = instruction.command(StubShip(), {}, dt=10.0)
        assert command.direction == Vec3(1.0, 0.0, 0.0)


# ----------------------------------------------------------------------
# Delta-v
# ----------------------------------------------------------------------

class TestDeltaV:
    def test_positive_delta_v_burns_prograde(self) -> None:
        ship = StubShip(velocity=Vec3(7.5, 0.0, 0.0))
        instruction = DeltaVInstruction(delta_v_km_s=0.1, duration=60.0)
        command = instruction.command(ship, {}, dt=60.0)
        assert command.direction == Vec3(1.0, 0.0, 0.0)

    def test_negative_delta_v_burns_retrograde(self) -> None:
        ship = StubShip(velocity=Vec3(7.5, 0.0, 0.0))
        instruction = DeltaVInstruction(delta_v_km_s=-0.1, duration=60.0)
        command = instruction.command(ship, {}, dt=60.0)
        assert command.direction == Vec3(-1.0, 0.0, 0.0)

    def test_reference_body_frame(self) -> None:
        """Prograde is relative to the reference body's velocity."""
        ship = StubShip(velocity=Vec3(30.0, 7.5, 0.0))
        earth = StubBody(velocity=Vec3(30.0, 0.0, 0.0))
        instruction = DeltaVInstruction(delta_v_km_s=0.1, duration=60.0,
                                        reference_body="Earth")
        command = instruction.command(ship, {"Earth": earth}, dt=60.0)
        # Ship velocity in Earth's frame is (0, 7.5, 0) -> prograde is +y
        assert command.direction == Vec3(0.0, 1.0, 0.0)

    def test_completes_when_delta_v_delivered(self) -> None:
        ship = StubShip()
        instruction = DeltaVInstruction(delta_v_km_s=0.01, duration=10.0)
        assert not instruction.is_complete()
        # A 10 m/s burn is tiny for this engine; one full step should do it.
        instruction.command(ship, {}, dt=10.0)
        assert instruction.is_complete()

    def test_throttle_capped_at_one_for_large_delta_v(self) -> None:
        ship = StubShip()
        instruction = DeltaVInstruction(delta_v_km_s=5.0, duration=1.0)
        command = instruction.command(ship, {}, dt=1.0)
        assert command.throttle == 1.0

    def test_rocket_equation_consistency(self) -> None:
        """The throttle sizing must invert the rocket equation exactly."""
        ship = StubShip()
        dv_target = 50.0  # m/s
        instruction = DeltaVInstruction(delta_v_km_s=dv_target / 1000.0,
                                        duration=10.0)
        command = instruction.command(ship, {}, dt=10.0)
        # Recompute the delta-v that this throttle actually delivers.
        fuel_burned = ship.max_thrust * command.throttle * 10.0 / ship.exhaust_velocity
        dv_delivered = ship.exhaust_velocity * log(
            ship.total_mass / (ship.total_mass - fuel_burned)
        )
        assert dv_delivered == pytest.approx(dv_target, rel=1e-9)


# ----------------------------------------------------------------------
# FlightPlan sequencing
# ----------------------------------------------------------------------

class TestFlightPlan:
    def test_empty_plan_coasts(self) -> None:
        plan = FlightPlan()
        command = plan.next_command(StubShip(), {}, dt=10.0)
        assert command.throttle == 0.0
        assert plan.is_complete()

    def test_instructions_execute_in_order(self) -> None:
        ship = StubShip()
        plan = (FlightPlan()
                .add_speed_up(throttle=1.0, duration=10.0)
                .add_coast(duration=10.0)
                .add_slow_down(throttle=1.0, duration=10.0))
        prograde = ship.velocity.normalized()

        first = plan.next_command(ship, {}, dt=10.0)
        second = plan.next_command(ship, {}, dt=10.0)
        third = plan.next_command(ship, {}, dt=10.0)
        fourth = plan.next_command(ship, {}, dt=10.0)  # plan exhausted

        assert first.direction == prograde and first.throttle == 1.0
        assert second.throttle == 0.0
        assert third.direction == -prograde and third.throttle == 1.0
        assert fourth.throttle == 0.0
        assert plan.is_complete()

    def test_instruction_spans_multiple_steps(self) -> None:
        plan = FlightPlan().add_speed_up(throttle=1.0, duration=30.0)
        ship = StubShip()
        for _ in range(3):
            command = plan.next_command(ship, {}, dt=10.0)
            assert command.throttle == 1.0
        assert plan.is_complete()
        assert plan.next_command(ship, {}, dt=10.0).throttle == 0.0

    def test_reset_rewinds_plan(self) -> None:
        ship = StubShip()
        plan = FlightPlan().add_coast(duration=10.0)
        plan.next_command(ship, {}, dt=10.0)
        assert plan.is_complete()
        plan.reset()
        assert not plan.is_complete()
        assert plan.current_instruction() is not None

    def test_reset_restores_delta_v_budget(self) -> None:
        ship = StubShip()
        plan = FlightPlan().add_delta_v(delta_v_km_s=0.01, duration=10.0)
        plan.next_command(ship, {}, dt=10.0)
        assert plan.is_complete()
        plan.reset()
        instruction = plan.current_instruction()
        assert isinstance(instruction, DeltaVInstruction)
        assert instruction.delta_v_remaining == pytest.approx(10.0)

    def test_add_at_index(self) -> None:
        plan = (FlightPlan()
                .add_coast(duration=10.0)
                .add_coast(duration=30.0))
        plan.add(CoastInstruction(duration=20.0), index=1)
        durations = [i.duration for i in plan.instructions]
        assert durations == [10.0, 20.0, 30.0]
