import * as THREE from "three";

// Mirrors app.py's LABEL_VERTICAL_OFFSET/LABEL_NUDGE_STEP/LABEL_NUDGE_ATTEMPTS,
// converted from Ursina's normalized UI space to CSS pixels.
const LABEL_VERTICAL_OFFSET_PX = 14;
const LABEL_NUDGE_STEP_PX = 16;
const LABEL_NUDGE_ATTEMPTS = 4;
const CHAR_WIDTH_PX = 7;
const LABEL_HEIGHT_PX = 14;

export interface LabelTarget {
  name: string;
  position: THREE.Vector3;
  color: string;
}

interface Placed {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Per-body/ship 2D name labels, positioned from their projected world
 * points and nudged vertically to avoid overlaps -- nearer targets get
 * first pick of their preferred spot. Mirrors app.py's update_labels. */
export class LabelLayer {
  private readonly els = new Map<string, HTMLDivElement>();
  private readonly container: HTMLElement;
  private readonly onDoubleClick: (name: string) => void;

  constructor(container: HTMLElement, onDoubleClick: (name: string) => void) {
    this.container = container;
    this.onDoubleClick = onDoubleClick;
  }

  update(camera: THREE.Camera, targets: LabelTarget[]): void {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const cameraPosition = camera.position;
    const cameraForward = new THREE.Vector3();
    camera.getWorldDirection(cameraForward);

    const candidates: (Placed & { name: string; color: string; dist: number })[] = [];
    const seen = new Set<string>();
    for (const target of targets) {
      seen.add(target.name);
      const toTarget = target.position.clone().sub(cameraPosition);
      const inFront = toTarget.dot(cameraForward) > 0;
      const ndc = target.position.clone().project(camera);
      if (!inFront || ndc.x < -1 || ndc.x > 1 || ndc.y < -1 || ndc.y > 1) {
        this.hide(target.name);
        continue;
      }
      const x = (ndc.x * 0.5 + 0.5) * width;
      const y = (-ndc.y * 0.5 + 0.5) * height - LABEL_VERTICAL_OFFSET_PX;
      candidates.push({
        name: target.name,
        x, y,
        w: Math.max(target.name.length * CHAR_WIDTH_PX, 20),
        h: LABEL_HEIGHT_PX,
        dist: toTarget.length(),
        color: target.color,
      });
    }
    candidates.sort((a, b) => a.dist - b.dist);

    const placed: Placed[] = [];
    for (const candidate of candidates) {
      let didPlace = false;
      for (let attempt = 0; attempt <= LABEL_NUDGE_ATTEMPTS && !didPlace; attempt++) {
        const directions = attempt === 0 ? [0] : [-1, 1];
        for (const direction of directions) {
          const y = candidate.y + direction * attempt * LABEL_NUDGE_STEP_PX;
          if (!this.overlaps(placed, candidate.x, y, candidate.w, candidate.h)) {
            this.show(candidate.name, candidate.x, y, candidate.color);
            placed.push({ x: candidate.x, y, w: candidate.w, h: candidate.h });
            didPlace = true;
            break;
          }
        }
      }
      if (!didPlace) this.hide(candidate.name);
    }

    for (const [name, el] of this.els) {
      if (!seen.has(name)) el.style.display = "none";
    }
  }

  private overlaps(placed: Placed[], x: number, y: number, w: number, h: number): boolean {
    for (const p of placed) {
      if (Math.abs(x - p.x) * 2 < w + p.w && Math.abs(y - p.y) * 2 < h + p.h) return true;
    }
    return false;
  }

  private show(name: string, x: number, y: number, color: string): void {
    let el = this.els.get(name);
    if (!el) {
      el = document.createElement("div");
      el.textContent = name;
      el.style.cssText =
        "position:fixed;font:12px monospace;text-shadow:0 0 3px #000;" +
        "pointer-events:auto;cursor:pointer;user-select:none;transform:translate(-50%,-100%);";
      el.addEventListener("dblclick", () => this.onDoubleClick(name));
      this.container.appendChild(el);
      this.els.set(name, el);
    }
    el.style.color = color;
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    el.style.display = "block";
  }

  private hide(name: string): void {
    const el = this.els.get(name);
    if (el) el.style.display = "none";
  }
}
