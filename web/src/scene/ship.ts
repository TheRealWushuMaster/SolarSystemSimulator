import * as THREE from "three";
import { POSITION_SCALE } from "./bodies";

// Matches app.py's MARKER_APPARENT_SIZE: the craft is always sub-pixel at
// solar-system scale, so it's rendered purely as a fixed-apparent-size dot.
const MARKER_APPARENT_SIZE = 0.004;
const MAX_TRAIL_POINTS = 4000;

export class ShipScene {
  readonly marker: THREE.Sprite;
  private readonly trailGeometry = new THREE.BufferGeometry();
  private readonly trailLine: THREE.Line;
  private readonly positions = new Float32Array(MAX_TRAIL_POINTS * 3);
  private trailCount = 0;

  constructor(color = 0x5fd0ff) {
    this.marker = new THREE.Sprite(new THREE.SpriteMaterial({ color, depthTest: true }));
    this.trailGeometry.setAttribute("position", new THREE.BufferAttribute(this.positions, 3));
    this.trailGeometry.setDrawRange(0, 0);
    this.trailLine = new THREE.Line(
      this.trailGeometry,
      new THREE.LineBasicMaterial({ color }),
    );
  }

  get group(): THREE.Object3D[] {
    return [this.marker, this.trailLine];
  }

  setColor(hexColor: string): void {
    const color = new THREE.Color(hexColor);
    (this.marker.material as THREE.SpriteMaterial).color = color;
    (this.trailLine.material as THREE.LineBasicMaterial).color = color;
  }

  setPosition(positionKm: [number, number, number], cameraPosition: THREE.Vector3): void {
    const [x, y, z] = positionKm;
    this.marker.position.set(x * POSITION_SCALE, z * POSITION_SCALE, y * POSITION_SCALE);
    const distance = this.marker.position.distanceTo(cameraPosition);
    this.marker.scale.setScalar(distance * MARKER_APPARENT_SIZE);
  }

  appendTrail(points: [number, number, number][]): void {
    for (const [x, y, z] of points) {
      if (this.trailCount >= MAX_TRAIL_POINTS) break;
      const offset = this.trailCount * 3;
      this.positions[offset] = x * POSITION_SCALE;
      this.positions[offset + 1] = z * POSITION_SCALE;
      this.positions[offset + 2] = y * POSITION_SCALE;
      this.trailCount++;
    }
    this.trailGeometry.attributes.position.needsUpdate = true;
    this.trailGeometry.setDrawRange(0, this.trailCount);
  }

  clearTrail(): void {
    this.trailCount = 0;
    this.trailGeometry.setDrawRange(0, 0);
  }
}
