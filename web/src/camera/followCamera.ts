import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

// Matches app.py's DEFAULT_CAMERA_Z/DEFAULT_CAMERA_PITCH: starting/reset zoom+tilt.
const DEFAULT_ZOOM = 60.0;
const DEFAULT_PITCH_DEG = 30.0;

export class FollowCamera {
  readonly camera: THREE.PerspectiveCamera;
  readonly controls: OrbitControls;
  private target: THREE.Vector3 = new THREE.Vector3();

  constructor(domElement: HTMLElement) {
    this.camera = new THREE.PerspectiveCamera(
      50,
      window.innerWidth / window.innerHeight,
      0.001,
      10000.0,
    );
    this.controls = new OrbitControls(this.camera, domElement);
    this.reset();
  }

  /** Escape: back to the Sun at the default pitch/zoom -- mirrors app.py's _reset_camera. */
  reset(): void {
    this.target.set(0, 0, 0);
    const pitch = THREE.MathUtils.degToRad(DEFAULT_PITCH_DEG);
    this.camera.position.set(
      0,
      DEFAULT_ZOOM * Math.sin(pitch),
      DEFAULT_ZOOM * Math.cos(pitch),
    );
    this.controls.target.copy(this.target);
    this.controls.update();
  }

  /** Re-center the orbit target on a followed body/ship's live position,
   * carrying the camera's offset along so the view doesn't jump -- mirrors
   * app.py's per-frame `camera_rig.position = self._follow_entity().position`. */
  follow(position: THREE.Vector3): void {
    const offset = this.camera.position.clone().sub(this.target);
    this.target.copy(position);
    this.controls.target.copy(this.target);
    this.camera.position.copy(this.target).add(offset);
  }

  update(): void {
    this.controls.update();
  }

  onResize(): void {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
  }
}
