import * as THREE from "three";

const loader = new THREE.TextureLoader();
const cache = new Map<string, THREE.Texture>();

export function loadTexture(filename: string): THREE.Texture {
  let texture = cache.get(filename);
  if (!texture) {
    texture = loader.load(`/textures/${filename}`);
    texture.colorSpace = THREE.SRGBColorSpace;
    cache.set(filename, texture);
  }
  return texture;
}
