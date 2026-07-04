/** The 'i'-toggled flight-plan panel -- mirrors app.py's plan_text, reusing
 * the server's pre-formatted [x]/[>]/[ ] instruction lines verbatim. */
export class FlightPlanPanel {
  private readonly el: HTMLDivElement;
  private visible = false;

  constructor(container: HTMLElement) {
    this.el = document.createElement("div");
    this.el.style.cssText =
      "position:fixed;top:100px;left:16px;font:13px monospace;color:#fff;" +
      "text-shadow:0 0 4px #000;white-space:pre;pointer-events:none;user-select:none;" +
      "display:none;";
    container.appendChild(this.el);
  }

  toggle(): void {
    this.visible = !this.visible;
    this.el.style.display = this.visible ? "block" : "none";
  }

  update(lines: string[]): void {
    if (!this.visible) return;
    this.el.textContent = "Flight plan\n" + lines.map((line) => "  " + line).join("\n");
  }
}
