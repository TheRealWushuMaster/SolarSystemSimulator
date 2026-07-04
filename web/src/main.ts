import * as THREE from "three";
import "./style.css";
import { SessionClient } from "./session/client";
import { BodyScene, SizeMode } from "./scene/bodies";
import { buildOrbitLines } from "./scene/orbitLines";
import { ShipScene } from "./scene/ship";
import { FollowCamera } from "./camera/followCamera";
import { Hud } from "./hud/hud";
import { ButtonMenu } from "./hud/menus";
import { FlightPlanPanel } from "./hud/flightPlanPanel";
import { LabelLayer } from "./hud/labels";
import { installKeybindings } from "./input/keybindings";

const TIME_STEP_COUNT = 11; // matches settings.py's simulation_steps length
const SHIP_NAME = "Ship";

async function main(): Promise<void> {
  const app = document.querySelector<HTMLDivElement>("#app")!;

  const client = new SessionClient();
  const [bodies, orbitLines, missions] = await Promise.all([
    client.fetchBodies(),
    client.fetchOrbitLines(),
    client.fetchMissions(),
  ]);
  await client.connect();
  client.send({ type: "set_play", playing: true });

  const scene = new THREE.Scene();
  const bodyScene = new BodyScene(bodies);
  const shipScene = new ShipScene();
  scene.add(bodyScene.group);
  scene.add(buildOrbitLines(orbitLines));
  scene.add(...shipScene.group);
  scene.add(new THREE.AmbientLight(0x2e2e38, 1.0));
  scene.add(new THREE.PointLight(0xffffff, 2.0, 0, 0));

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  app.appendChild(renderer.domElement);

  const followCamera = new FollowCamera(renderer.domElement);
  const hud = new Hud(app);
  const planPanel = new FlightPlanPanel(app);
  const labels = new LabelLayer(app, (name) => client.send({ type: "set_follow", target: name }));

  const planetNames = Object.entries(bodies)
    .filter(([, entry]) => entry.parent_body === "Sun")
    .map(([name]) => name);
  const followNames = [...bodyScene.names(), SHIP_NAME];

  const flyMenu = new ButtonMenu(app, "Fly to:");
  const homeMenu = new ButtonMenu(app, "Start at:");
  const missionMenu = new ButtonMenu(app, "Mission:");

  let homeBody = "Earth";
  function refreshFlyMenu(): void {
    flyMenu.setItems(planetNames, "#2a6fbf", (name) => {
      flyMenu.setOpen(false);
      void client.flyTo(name).then((result) => {
        hud.notify(result.status === "ok"
          ? (result.mission_label ?? `Flying to ${name}.`)
          : (result.message ?? `No transfer window found to ${name}.`));
      });
    });
    flyMenu.setDisabled(homeBody, true);
  }
  refreshFlyMenu();
  homeMenu.setItems(planetNames, "#2fa84f", (name) => {
    homeMenu.setOpen(false);
    void client.setHome(name).then((result) => {
      if (result.status === "ok") {
        homeBody = name;
        refreshFlyMenu();
        hud.notify(`Home set to ${name}.`);
      }
    });
  });
  missionMenu.setItems([...Object.keys(missions), "Earth-Moon trip"], "#c9772f", (name) => {
    missionMenu.setOpen(false);
    void client.loadMission(name).then((result) => {
      hud.notify(result.mission_label ?? `Loaded ${name}.`);
    });
  });

  let sizeMode: SizeMode = SizeMode.LOG;
  let timeStepIndex = 7; // "1 day", matches server's DEFAULT_TIME_STEP_INDEX

  function closeMenus(): void {
    flyMenu.setOpen(false);
    homeMenu.setOpen(false);
    missionMenu.setOpen(false);
  }

  function lastPlaying(): boolean {
    return client.latestState?.hud.playing ?? false;
  }

  installKeybindings({
    togglePlay: () => client.send({ type: "set_play", playing: !lastPlaying() }),
    reverse: () => client.send({ type: "reverse" }),
    toggleSizeMode: () => {
      sizeMode = sizeMode === SizeMode.LOG ? SizeMode.REAL : SizeMode.LOG;
    },
    toggleTestDrive: () => client.send({ type: "toggle_test_drive" }),
    toggleFlyMenu: () => {
      const wasOpen = flyMenu.isOpen();
      closeMenus();
      if (!wasOpen) flyMenu.setOpen(true);
    },
    toggleHomeMenu: () => {
      const wasOpen = homeMenu.isOpen();
      closeMenus();
      if (!wasOpen) homeMenu.setOpen(true);
    },
    toggleMissionMenu: () => {
      const wasOpen = missionMenu.isOpen();
      closeMenus();
      if (!wasOpen) missionMenu.setOpen(true);
    },
    stepTime: (direction) => client.send({ type: "step", direction }),
    changeTimeStep: (delta) => {
      timeStepIndex = Math.max(0, Math.min(timeStepIndex + delta, TIME_STEP_COUNT - 1));
      client.send({ type: "set_time_step", index: timeStepIndex });
    },
    cycleFollow: () => {
      const current = client.latestState?.hud.following ?? followNames[0];
      const next = followNames[(followNames.indexOf(current) + 1) % followNames.length];
      client.send({ type: "set_follow", target: next });
    },
    resetCamera: () => {
      followCamera.reset();
      client.send({ type: "set_follow", target: "Sun" });
    },
    togglePlanPanel: () => planPanel.toggle(),
    exportTrajectory: () => {
      void client.exportTrajectory().then((result) => {
        if (!result.ok || !result.text) {
          hud.notify("Nothing to export -- fly a mission first.");
          return;
        }
        const blob = new Blob([result.text], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "solara_trajectory.csv";
        link.click();
        URL.revokeObjectURL(url);
        hud.notify("Trajectory exported.");
      });
    },
  });

  // Double-click a body to follow it.
  const raycaster = new THREE.Raycaster();
  renderer.domElement.addEventListener("dblclick", (event) => {
    const pointer = new THREE.Vector2(
      (event.clientX / window.innerWidth) * 2 - 1,
      -(event.clientY / window.innerHeight) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, followCamera.camera);
    const meshes = [
      ...bodyScene.names().map((name) => bodyScene.mesh(name)),
      shipScene.marker,
    ].filter((mesh): mesh is THREE.Object3D => mesh !== null);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    if (!hit) return;
    if (hit.object === shipScene.marker) {
      client.send({ type: "set_follow", target: SHIP_NAME });
      return;
    }
    const name = bodyScene.names().find((n) => bodyScene.mesh(n) === hit.object);
    if (name) client.send({ type: "set_follow", target: name });
  });

  window.addEventListener("resize", () => {
    renderer.setSize(window.innerWidth, window.innerHeight);
    followCamera.onResize();
  });

  let lastMissionLabel = "";

  function renderLoop(): void {
    requestAnimationFrame(renderLoop);
    client.tick();
    const state = client.latestState;
    if (state) {
      for (const [name, { p }] of Object.entries(state.bodies)) {
        bodyScene.setPosition(name, p);
      }
      bodyScene.applySizes(sizeMode, followCamera.camera.position);
      bodyScene.updateSpin(state.sim_time_s);
      shipScene.setPosition(state.ship.p, followCamera.camera.position);
      if (state.ship.trail_reset) shipScene.clearTrail();
      shipScene.appendTrail(state.ship.trail_append);

      const labelTargets = bodyScene.names()
        .map((name) => ({ name, position: bodyScene.position(name), color: "#ffffff" }))
        .filter((t): t is { name: string; position: THREE.Vector3; color: string } => t.position !== null);
      labelTargets.push({ name: SHIP_NAME, position: shipScene.marker.position, color: "#5fd0ff" });
      labels.update(followCamera.camera, labelTargets);

      const followPos = state.hud.following === SHIP_NAME
        ? shipScene.marker.position
        : bodyScene.position(state.hud.following);
      if (followPos) followCamera.follow(followPos);

      hud.update(state.hud, state.date, sizeMode);
      planPanel.update(state.plan);
      if (state.hud.mission_label !== lastMissionLabel) {
        lastMissionLabel = state.hud.mission_label;
        homeBody = state.hud.home_body;
        refreshFlyMenu();
      }
    }
    followCamera.update();
    renderer.render(scene, followCamera.camera);
  }
  renderLoop();
}

main().catch((error: unknown) => {
  console.error("Failed to start Solara web client:", error);
});
