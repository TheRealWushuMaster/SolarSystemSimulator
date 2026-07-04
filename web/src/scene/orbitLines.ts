import * as THREE from "three";
import { POSITION_SCALE } from "./bodies";

export type OrbitLines = Record<string, [number, number, number][]>;

/** Static per-body ecliptic loops -- fetched once, built once, never updated
 * per tick (mirrors app.py's _draw_orbit_lines, which samples at scene-build
 * time rather than every frame). */
export function buildOrbitLines(lines: OrbitLines): THREE.Group {
  const group = new THREE.Group();
  const material = new THREE.LineBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.15,
  });
  for (const points of Object.values(lines)) {
    const vertices = points.flatMap(([x, y, z]) => [
      x * POSITION_SCALE,
      z * POSITION_SCALE,
      y * POSITION_SCALE,
    ]);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    group.add(new THREE.LineLoop(geometry, material));
  }
  return group;
}
