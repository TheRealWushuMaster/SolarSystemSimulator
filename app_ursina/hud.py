from __future__ import annotations
from ursina import Text, camera, mouse

from app_ursina.config import (LABEL_NUDGE_ATTEMPTS, LABEL_NUDGE_STEP,
                               LABEL_VERTICAL_OFFSET)
from core.flight_plan import (CoastInstruction, DeltaVInstruction,
                              OrbitInsertionInstruction, ThrustInstruction,
                              VectorBurnInstruction)


class HudMixin:
    """HUD text, screen-space labels and the flight-plan panel."""

    def refresh_hud(self) -> None:
        self.date_text.text = f"{self.current_date:%Y-%m-%d %H:%M:%S}"
        play_state: str = ("RUNNING" if self.play_direction > 0 else "REVERSED") \
            if self.auto_play else "PAUSED"
        self.status_text.text = (f"Step: {self.time_step_name}  [{play_state}]"
                                 f"   Sizes: {self.size_mode.name}"
                                 + ("   [TEST DRIVE]" if self.use_test_ship else ""))
        self.follow_text.text = f"Following: {self.follow_names[self.follow_index]}"
        self.mission_text.text = f"Mission: {self.mission_label}" if self.mission_label else ""

    def update_labels(self) -> None:
        """
        Per-frame: place 2D labels over their projected world points,
        nudging vertically to avoid overlaps (closest body wins its
        preferred spot). Crude but good enough.
        """
        # `camera.lens` (needed by screen_position) only exists once a
        # render window is up; skip in headless mode.
        if not hasattr(camera, "lens"):
            return
        cam_pos = camera.world_position
        cam_fwd = camera.forward
        half_width = camera.aspect_ratio / 2.0

        # Gather visible candidates with their camera distance.
        candidates: list[tuple[float, Text, str, float, float]] = []
        for text, entity, name in self._label_targets:
            to_entity = entity.world_position - cam_pos
            in_front = (to_entity.x * cam_fwd.x
                        + to_entity.y * cam_fwd.y
                        + to_entity.z * cam_fwd.z) > 0
            screen = entity.screen_position
            if not in_front or abs(screen.x) > half_width or abs(screen.y) > 0.5:
                text.enabled = False
                continue
            candidates.append((to_entity.length(), text, name,
                               screen.x, screen.y + LABEL_VERTICAL_OFFSET))

        # Nearer bodies get first pick of their preferred position.
        candidates.sort(key=lambda c: c[0])
        self._label_hitboxes = []
        for _, text, name, x, y0 in candidates:
            w = max(text.width, 0.05)
            h = max(text.height, 0.03)
            placed = False
            for attempt in range(LABEL_NUDGE_ATTEMPTS + 1):
                for direction in ((1, -1) if attempt else (0,)):
                    y = y0 + direction * attempt * LABEL_NUDGE_STEP
                    if not self._overlaps_placed(x, y, w, h):
                        text.position = (x, y)
                        text.enabled = True
                        self._label_hitboxes.append((name, x, y, w, h))
                        placed = True
                        break
                if placed:
                    break
            text.enabled = placed

    def _overlaps_placed(self, x: float, y: float, w: float, h: float) -> bool:
        for _, px, py, pw, ph in self._label_hitboxes:
            if abs(x - px) * 2 < (w + pw) and abs(y - py) * 2 < (h + ph):
                return True
        return False

    def _follow_at_pointer(self) -> None:
        """Double-click: follow the hovered body, or a clicked label."""
        hovered = mouse.hovered_entity
        if hovered is not None and hasattr(hovered, "body_name"):
            self.follow(hovered.body_name)
            return
        mx, my = mouse.position.x, mouse.position.y
        for name, x, y, w, h in self._label_hitboxes:
            if abs(mx - x) * 2 <= w and abs(my - y) * 2 <= h:
                self.follow(name)
                return

    # ------------------------------------------------------------------
    # Flight-plan panel
    # ------------------------------------------------------------------

    def _refresh_plan_panel(self) -> None:
        self.plan_text.text = "Flight plan\n" + "\n".join(self._plan_lines())

    def _plan_lines(self) -> list[str]:
        if self.sim_ship is None:
            return ["  (parked — no active flight)"]
        if self.moon_trip:
            return self._moon_plan_lines()
        plan = self.sim_ship.flight_plan
        plan.current_instruction()          # advance past any completed steps
        if not plan.instructions:
            return ["  (coasting — no instructions)"]
        lines: list[str] = []
        for index, instruction in enumerate(plan.instructions):
            if index < plan.current_index:
                mark = "[x]"
            elif index == plan.current_index:
                mark = "[>]"
            else:
                mark = "[ ]"
            lines.append(f"  {mark} {self._describe_instruction(instruction)}")
        return lines

    def _moon_plan_lines(self) -> list[str]:
        returned = not self._moon_returning      # the return burn has fired
        arrived = self._moon_arrived
        return [
            f"  {'[x]' if returned else '[>]'} Hohmann transfer out to the Moon",
            f"  {'[x]' if arrived else ('[>]' if returned else '[ ]')} "
            f"Return burn at the Moon, coast back to Earth",
            f"  {'[x]' if arrived else '[ ]'} Circularize in low Earth orbit",
        ]

    def _describe_instruction(self, instruction) -> str:
        if isinstance(instruction, CoastInstruction):
            return f"Coast {instruction.duration / 86400.0:.2f} d"
        if isinstance(instruction, VectorBurnInstruction):
            return (f"Burn {instruction.delta_v_remaining / 1000.0:.3f} km/s left "
                    f"(of {instruction._initial_delta_v / 1000.0:.3f})")
        if isinstance(instruction, DeltaVInstruction):
            return f"Burn delta-v {instruction.delta_v_km_s:+.3f} km/s"
        if isinstance(instruction, OrbitInsertionInstruction):
            if instruction._inserted:
                state = "inserted"
            elif instruction._capturing:
                state = "capturing"
            else:
                state = "approaching"
            return f"Orbit insertion at {instruction.target_body} ({state})"
        if isinstance(instruction, ThrustInstruction):
            return f"Thrust {instruction.throttle:.0%}"
        return instruction.__class__.__name__
