import * as THREE from "three";
import { loadTexture } from "./textures";

const RING_TEXTURE = "2k_saturn_ring_alpha.png";

/**
 * A flat annulus in the local xz-plane, radii in local (sphere-radius-1)
 * units, with UVs mapping the radial direction across u -- mirrors app.py's
 * make_ring_mesh so a ring texture's radial bands land in the right place.
 */
function ringGeometry(inner: number, outer: number, segments = 64): THREE.BufferGeometry {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  for (let i = 0; i <= segments; i++) {
    const angle = (2 * Math.PI * i) / segments;
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    positions.push(inner * c, 0, inner * s, outer * c, 0, outer * s);
    uvs.push(0, 0.5, 1, 0.5);
  }
  for (let i = 0; i < segments; i++) {
    const b = 2 * i;
    indices.push(b, b + 1, b + 3, b, b + 3, b + 2);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  return geometry;
}

/** Ring value (bodies.json's "rings" count) -> a ring mesh, or null if the
 * body has none. >=3 (Saturn) gets the textured alpha ring; 1-2 (Jupiter/
 * Uranus/Neptune) get a faint flat tint, matching app.py's _add_rings. */
export function buildRingMesh(ringValue: number): THREE.Mesh | null {
  if (ringValue <= 0) return null;
  if (ringValue >= 3) {
    const geometry = ringGeometry(0.7, 1.5);
    const material = new THREE.MeshBasicMaterial({
      map: loadTexture(RING_TEXTURE),
      color: 0xffffff,
      transparent: true,
      side: THREE.DoubleSide,
    });
    return new THREE.Mesh(geometry, material);
  }
  const geometry = ringGeometry(0.65, 1.05);
  const material = new THREE.MeshBasicMaterial({
    color: 0xcdd1d9,
    transparent: true,
    opacity: 0.18,
    side: THREE.DoubleSide,
  });
  return new THREE.Mesh(geometry, material);
}
