from __future__ import annotations
from ursina import Button, Text, color as ursina_color

from app_ursina.config import MOON_TRIP_NAME


class MenuMixin:
    """Hidden vertical button menus: set-home ('h'), fly-to ('f'), mission ('v')."""

    def _build_menus(self) -> None:
        self.fly_menu_open: bool = False
        self.home_menu_open: bool = False
        self.mission_menu_open: bool = False
        self.fly_title, self.fly_buttons = self._build_button_menu(
            "Fly to:", x=0.72, color=ursina_color.azure, on_pick=self._fly_to)
        self.home_title, self.home_buttons = self._build_button_menu(
            "Start at:", x=0.72, color=ursina_color.lime, on_pick=self._set_home)
        self.mission_menu_title, self.mission_buttons = self._build_button_menu(
            "Mission:", x=0.72, color=ursina_color.orange, on_pick=self._load_mission,
            names=list(self.missions.keys()) + [MOON_TRIP_NAME])

    def _build_button_menu(self, title: str, x: float, color, on_pick,
                           names: list[str] | None = None) -> tuple[Text, dict[str, Button]]:
        if names is None:
            names = [name for name, body in self.bodies.items()
                     if body.parent_body == "Sun"]
        title_text = Text(text=title, position=(x - 0.10, 0.45), scale=0.9,
                          color=color, enabled=False)
        buttons: dict[str, Button] = {}
        for i, name in enumerate(names):
            button = Button(text=name, scale=(0.2, 0.05),
                            position=(x, 0.38 - i * 0.06),
                            color=color.tint(-0.4), enabled=False)
            button.on_click = (lambda target=name: on_pick(target))
            buttons[name] = button
        return title_text, buttons

    def _toggle_fly_menu(self) -> None:
        was_open = self.fly_menu_open
        self._close_menus()
        if not was_open:
            self._set_fly_menu(True)

    def _toggle_home_menu(self) -> None:
        was_open = self.home_menu_open
        self._close_menus()
        if not was_open:
            self._set_home_menu(True)

    def _toggle_mission_menu(self) -> None:
        was_open = self.mission_menu_open
        self._close_menus()
        if not was_open:
            self._set_mission_menu(True)

    def _close_menus(self) -> None:
        self._set_fly_menu(False)
        self._set_home_menu(False)
        self._set_mission_menu(False)

    def _set_fly_menu(self, open_: bool) -> None:
        self.fly_menu_open = open_
        self.fly_title.enabled = open_
        for name, button in self.fly_buttons.items():
            button.enabled = open_ and name != self.home_body   # can't fly to where you are

    def _set_home_menu(self, open_: bool) -> None:
        self.home_menu_open = open_
        self.home_title.enabled = open_
        for button in self.home_buttons.values():
            button.enabled = open_

    def _set_mission_menu(self, open_: bool) -> None:
        self.mission_menu_open = open_
        self.mission_menu_title.enabled = open_
        for button in self.mission_buttons.values():
            button.enabled = open_
