"""Wire-format helpers: core/ objects -> plain JSON-able dicts."""

from __future__ import annotations

from typing import Any

from core.flight_plan import (
    CoastInstruction,
    DeltaVInstruction,
    Instruction,
    OrbitInsertionInstruction,
    ThrustInstruction,
    VectorBurnInstruction,
)
from core.moon_transfer import MoonMissionPhase
from core.vec3 import Vec3


def vec3_pair(position: Vec3, velocity: Vec3) -> dict[str, list[float]]:
    return {
        "p": [position.x, position.y, position.z],
        "v": [velocity.x, velocity.y, velocity.z],
    }


def _describe_instruction(instruction: Instruction) -> str:
    if isinstance(instruction, CoastInstruction):
        return f"Coast {instruction.duration / 86400.0:.2f} d"
    if isinstance(instruction, VectorBurnInstruction):
        return (f"Burn {instruction.delta_v_remaining / 1000.0:.3f} km/s left "
                f"(of {instruction._initial_delta_v / 1000.0:.3f})")
    if isinstance(instruction, DeltaVInstruction):
        return f"Burn delta-v {instruction.delta_v_km_s:+.3f} km/s"
    if isinstance(instruction, OrbitInsertionInstruction):
        state = "inserted" if instruction._inserted else ("capturing" if instruction._capturing
                                                           else "approaching")
        return f"Orbit insertion at {instruction.target_body} ({state})"
    if isinstance(instruction, ThrustInstruction):
        return f"Thrust {instruction.throttle:.0%}"
    return instruction.__class__.__name__


def _moon_plan_lines(session: Any) -> list[str]:
    phase = session.moon_state.phase
    returned = phase is not MoonMissionPhase.OUTBOUND
    arrived = phase is MoonMissionPhase.CIRCULARIZED
    return [
        f"{'[x]' if returned else '[>]'} Hohmann transfer out to the Moon",
        f"{'[x]' if arrived else ('[>]' if returned else '[ ]')} "
        f"Return burn at the Moon, coast back to Earth",
        f"{'[x]' if arrived else '[ ]'} Circularize in low Earth orbit",
    ]


def plan_lines(session: Any) -> list[str]:
    """Mirrors app.py's _plan_lines/_moon_plan_lines -- reuses the same
    pre-formatted strings rather than inventing a structured wire format."""
    if session.sim_ship is None:
        return ["(parked -- no active flight)"]
    if session.moon_trip and session.moon_state is not None:
        return _moon_plan_lines(session)
    plan = session.sim_ship.flight_plan
    plan.current_instruction()   # advance past any completed steps
    if not plan.instructions:
        return ["(coasting -- no instructions)"]
    lines: list[str] = []
    for index, instruction in enumerate(plan.instructions):
        mark = "[x]" if index < plan.current_index else ("[>]" if index == plan.current_index
                                                          else "[ ]")
        lines.append(f"{mark} {_describe_instruction(instruction)}")
    return lines


def state_message(session: Any, trail_append: list[Vec3], trail_reset: bool = False) -> dict[str, Any]:
    """Build the per-tick 'state' push described in the web-port plan."""
    bodies: dict[str, dict[str, list[float]]] = {
        name: vec3_pair(body.position, body.velocity)
        for name, body in session.bodies.items()
    }
    message: dict[str, Any] = {
        "type": "state",
        "sim_time_s": session.sim_time_s,
        "date": session.current_date.isoformat(),
        "bodies": bodies,
        "ship": {
            **vec3_pair(session.ship_position(), session.ship_velocity()),
            "trail_append": [[p.x, p.y, p.z] for p in trail_append],
            "trail_reset": trail_reset,
        },
        "hud": {
            "time_step_name": session.time_step_name,
            "playing": session.auto_play,
            "direction": session.play_direction,
            "following": session.follow_target,
            "home_body": session.home_body,
            "test_drive": session.use_test_ship,
            "mission_label": session.mission_label,
            "notification": session.last_notification,
        },
        "plan": plan_lines(session),
    }
    return message
