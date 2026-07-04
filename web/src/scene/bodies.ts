import * as THREE from "three";
import type { BodyCatalogue } from "../session/wireTypes";
import { loadTexture } from "./textures";
import { buildRingMesh } from "./rings";

// Matches app.py's POSITION_SCALE: 1 scene unit = 10 million km.
export const POSITION_SCALE = 1e-7;

// Matches app.py's MARKER_APPARENT_SIZE: fraction of camera distance that
// gives a marker dot of ~2-3px radius at the default field of view.
const MARKER_APPARENT_SIZE = 0.004;

// Axial tilt (obliquity to the ecliptic), degrees -- mirrors app.py's
// AXIAL_TILT_DEG. Values > 90 spin retrograde (Venus, Uranus, Pluto).
const AXIAL_TILT_DEG: Record<string, number> = {
  Sun: 7.25,
  Mercury: 0.03,
  Venus: 177.4,
  Earth: 23.44,
  Moon: 6.68,
  Mars: 25.19,
  Jupiter: 3.13,
  Saturn: 26.73,
  Uranus: 97.77,
  Neptune: 28.32,
  Pluto: 122.53,
};

export const SizeMode = { LOG: "LOG", REAL: "REAL" } as const;
export type SizeMode = (typeof SizeMode)[keyof typeof SizeMode];

// Matches app.py's log_diameter(): everything visible at once regardless of
// true scale (Moon ~0.66, Earth ~0.92, Jupiter ~1.9, Sun ~2.8).
function logDiameter(radiusKm: number): number {
  return Math.max(0.15, 0.2 * Math.log10(radiusKm / 10.0)) * 2.0;
}

// True diameter in scene units -- often sub-pixel, hence the marker dot.
function realDiameter(radiusKm: number): number {
  return 2.0 * radiusKm * POSITION_SCALE;
}

interface Body {
  tiltFrame: THREE.Group;
  globe: THREE.Mesh;
  marker: THREE.Sprite;
  radiusKm: number;
  rotationPeriodS: number;
}

export class BodyScene {
  readonly group = new THREE.Group();
  private readonly bodiesByName = new Map<string, Body>();

  constructor(catalogue: BodyCatalogue) {
    for (const [name, entry] of Object.entries(catalogue)) {
      const tiltFrame = new THREE.Group();
      tiltFrame.rotation.z = THREE.MathUtils.degToRad(AXIAL_TILT_DEG[name] ?? 0);

      const geometry = new THREE.SphereGeometry(0.5, 32, 32);
      const texture = entry.texture ? loadTexture(entry.texture) : null;
      // The star is unlit (it's its own light source, so shading it against
      // the scene's Sun-point-light would self-shadow it into a crescent) --
      // MeshBasicMaterial shows the texture as-is with no lighting math,
      // matching app.py's `unlit=is_star`. Planets stay lit (MeshStandardMaterial).
      const material = entry.is_star
        ? new THREE.MeshBasicMaterial({ color: texture ? 0xffffff : entry.color })
        : new THREE.MeshStandardMaterial({ color: texture ? 0xffffff : entry.color });
      if (texture) material.map = texture;
      const globe = new THREE.Mesh(geometry, material);
      globe.scale.setScalar(logDiameter(entry.radius_km));
      tiltFrame.add(globe);

      const ring = buildRingMesh(entry.rings);
      if (ring) globe.add(ring);

      const marker = new THREE.Sprite(
        new THREE.SpriteMaterial({ color: entry.color, depthTest: true }),
      );
      marker.visible = false;
      tiltFrame.add(marker);

      tiltFrame.name = name;
      this.group.add(tiltFrame);
      this.bodiesByName.set(name, {
        tiltFrame, globe, marker,
        radiusKm: entry.radius_km,
        rotationPeriodS: entry.rotation_period_s,
      });
    }
  }

  /** Spin each globe about its (tilted) polar axis for the given sim time --
   * mirrors app.py's BodyEntity.update_spin. */
  updateSpin(simTimeS: number): void {
    for (const body of this.bodiesByName.values()) {
      if (body.rotationPeriodS > 0) {
        body.globe.rotation.y = ((simTimeS / body.rotationPeriodS) % 1.0) * 2.0 * Math.PI;
      }
    }
  }

  /** heliocentric km -> scene units, with app.py's (x, z, y) axis swap for Y-up. */
  setPosition(name: string, positionKm: [number, number, number]): void {
    const body = this.bodiesByName.get(name);
    if (!body) return;
    const [x, y, z] = positionKm;
    body.tiltFrame.position.set(x * POSITION_SCALE, z * POSITION_SCALE, y * POSITION_SCALE);
  }

  /** Per-frame: apparent size depends on camera distance in REAL mode, and
   * the marker dot substitutes for a sub-pixel real sphere -- mirrors
   * app.py's BodyEntity.apply_size. */
  applySizes(mode: SizeMode, cameraPosition: THREE.Vector3): void {
    for (const body of this.bodiesByName.values()) {
      const distance = body.tiltFrame.position.distanceTo(cameraPosition);
      if (mode === SizeMode.LOG) {
        body.globe.scale.setScalar(logDiameter(body.radiusKm));
        body.marker.visible = false;
      } else {
        const diameter = realDiameter(body.radiusKm);
        body.globe.scale.setScalar(diameter);
        const markerSize = distance * MARKER_APPARENT_SIZE;
        body.marker.scale.setScalar(markerSize);
        body.marker.visible = diameter < markerSize;
      }
    }
  }

  position(name: string): THREE.Vector3 | null {
    return this.bodiesByName.get(name)?.tiltFrame.position ?? null;
  }

  names(): string[] {
    return [...this.bodiesByName.keys()];
  }

  mesh(name: string): THREE.Object3D | null {
    return this.bodiesByName.get(name)?.globe ?? null;
  }
}
