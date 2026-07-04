/** Vertical button menus (fly-to / start-at / mission) -- mirrors app.py's
 * _build_button_menu. Pure DOM buttons positioned top-right, toggled by the
 * f/h/v keybindings. */
export class ButtonMenu {
  private readonly titleEl: HTMLDivElement;
  private readonly listEl: HTMLDivElement;
  private open = false;

  constructor(container: HTMLElement, title: string) {
    this.titleEl = document.createElement("div");
    this.titleEl.textContent = title;
    this.titleEl.style.cssText =
      "position:fixed;top:12px;right:16px;font:15px monospace;color:#fff;" +
      "display:none;user-select:none;";
    this.listEl = document.createElement("div");
    this.listEl.style.cssText =
      "position:fixed;top:36px;right:16px;display:none;flex-direction:column;gap:4px;";
    container.append(this.titleEl, this.listEl);
  }

  setItems(names: string[], color: string, onPick: (name: string) => void): void {
    this.titleEl.style.color = color;
    this.listEl.innerHTML = "";
    for (const name of names) {
      const button = document.createElement("button");
      button.textContent = name;
      button.style.cssText =
        `font:13px monospace;color:#fff;background:${color};border:none;` +
        "border-radius:3px;padding:4px 10px;cursor:pointer;width:140px;";
      button.onclick = () => onPick(name);
      this.listEl.appendChild(button);
    }
  }

  setDisabled(name: string, disabled: boolean): void {
    for (const button of this.listEl.querySelectorAll("button")) {
      if (button.textContent === name) (button as HTMLButtonElement).disabled = disabled;
    }
  }

  toggle(): boolean {
    this.setOpen(!this.open);
    return this.open;
  }

  setOpen(open: boolean): void {
    this.open = open;
    this.titleEl.style.display = open ? "block" : "none";
    this.listEl.style.display = open ? "flex" : "none";
  }

  isOpen(): boolean {
    return this.open;
  }
}
