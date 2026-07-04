import type { HudState } from "../session/wireTypes";

const HELP_TEXT =
  "space play | arrows step/timestep | dbl-click/tab follow | m sizes | r reverse | " +
  "h start at | f fly to | v mission | t test drive | i plan | e export | esc reset";

export class Hud {
  private readonly dateEl: HTMLDivElement;
  private readonly statusEl: HTMLDivElement;
  private readonly followEl: HTMLDivElement;
  private readonly missionEl: HTMLDivElement;
  private readonly noteEl: HTMLDivElement;
  private noteTimeout: number | null = null;
  private lastServerNotification = "";

  constructor(container: HTMLElement) {
    const panel = document.createElement("div");
    panel.style.cssText =
      "position:fixed;top:12px;left:16px;font:14px/1.5 monospace;" +
      "color:#fff;text-shadow:0 0 4px #000;pointer-events:none;user-select:none;";
    this.dateEl = document.createElement("div");
    this.statusEl = document.createElement("div");
    this.statusEl.style.color = "#ffe066";
    this.followEl = document.createElement("div");
    this.followEl.style.color = "#7CFC7C";
    this.missionEl = document.createElement("div");
    this.missionEl.style.color = "#5fd0ff";
    this.noteEl = document.createElement("div");
    panel.append(this.dateEl, this.statusEl, this.followEl, this.missionEl, this.noteEl);
    container.appendChild(panel);

    const help = document.createElement("div");
    help.textContent = HELP_TEXT;
    help.style.cssText =
      "position:fixed;bottom:10px;left:16px;font:12px monospace;" +
      "color:rgba(255,255,255,0.5);pointer-events:none;user-select:none;";
    container.appendChild(help);
  }

  update(hud: HudState, date: string, sizeMode: string): void {
    this.dateEl.textContent = new Date(date).toISOString().replace("T", " ").slice(0, 19);
    const playState = hud.playing ? (hud.direction > 0 ? "RUNNING" : "REVERSED") : "PAUSED";
    this.statusEl.textContent =
      `Step: ${hud.time_step_name}  [${playState}]   Sizes: ${sizeMode}` +
      (hud.test_drive ? "   [TEST DRIVE]" : "");
    this.followEl.textContent = `Following: ${hud.following}`;
    this.missionEl.textContent = hud.mission_label ? `Mission: ${hud.mission_label}` : "";
    if (hud.notification && hud.notification !== this.lastServerNotification) {
      this.lastServerNotification = hud.notification;
      this.notify(hud.notification);
    }
  }

  notify(message: string): void {
    this.noteEl.textContent = message;
    if (this.noteTimeout !== null) window.clearTimeout(this.noteTimeout);
    this.noteTimeout = window.setTimeout(() => {
      this.noteEl.textContent = "";
    }, 4000);
  }
}
