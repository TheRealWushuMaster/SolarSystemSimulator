/** The 13 keybindings from app.py's input(), dispatched to callback hooks so
 * the actual state changes stay in main.ts rather than duplicated here. */
export interface KeybindingHandlers {
  togglePlay(): void;
  reverse(): void;
  toggleSizeMode(): void;
  toggleTestDrive(): void;
  toggleFlyMenu(): void;
  toggleHomeMenu(): void;
  toggleMissionMenu(): void;
  stepTime(direction: number): void;
  changeTimeStep(delta: number): void;
  cycleFollow(): void;
  resetCamera(): void;
  togglePlanPanel(): void;
  exportTrajectory(): void;
}

export function installKeybindings(handlers: KeybindingHandlers): void {
  window.addEventListener("keydown", (event) => {
    switch (event.key) {
      case " ":
        event.preventDefault();
        handlers.togglePlay();
        break;
      case "r":
        handlers.reverse();
        break;
      case "m":
        handlers.toggleSizeMode();
        break;
      case "t":
        handlers.toggleTestDrive();
        break;
      case "f":
        handlers.toggleFlyMenu();
        break;
      case "h":
        handlers.toggleHomeMenu();
        break;
      case "v":
        handlers.toggleMissionMenu();
        break;
      case "ArrowRight":
        handlers.stepTime(1);
        break;
      case "ArrowLeft":
        handlers.stepTime(-1);
        break;
      case "ArrowUp":
        handlers.changeTimeStep(1);
        break;
      case "ArrowDown":
        handlers.changeTimeStep(-1);
        break;
      case "Tab":
        event.preventDefault();
        handlers.cycleFollow();
        break;
      case "Escape":
        handlers.resetCamera();
        break;
      case "i":
        handlers.togglePlanPanel();
        break;
      case "e":
        handlers.exportTrajectory();
        break;
    }
  });
}
