import type {
  BodyCatalogue,
  Command,
  MissionCatalogue,
  OrbitLinesResponse,
  StateMessage,
} from "./wireTypes";

// In production this is served from the same origin as the app (Caddy
// proxies /api and /ws to the backend), so an empty base just works. In dev,
// Vite serves the frontend on its own port and the backend runs separately.
const API_BASE: string = import.meta.env.DEV ? "http://localhost:8000" : "";
const WS_BASE: string = import.meta.env.DEV ? "ws://localhost:8000" : `wss://${location.host}`;

export class SessionClient {
  private socket: WebSocket | null = null;
  private sessionId: string | null = null;
  latestState: StateMessage | null = null;

  async connect(): Promise<void> {
    const response = await fetch(`${API_BASE}/api/session`, { method: "POST" });
    const { session_id } = (await response.json()) as { session_id: string };
    this.sessionId = session_id;
    return this.openSocket();
  }

  private openSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(`${WS_BASE}/ws/session/${this.sessionId}`);
      let opened = false;
      socket.onopen = () => {
        opened = true;
        resolve();
      };
      socket.onerror = (event) => {
        if (!opened) reject(event);
      };
      socket.onmessage = (event) => {
        this.latestState = JSON.parse(event.data) as StateMessage;
      };
      // The server never drops a live session on a dropped socket (a network
      // blip, a backgrounded tab) -- reconnecting to the same session_id
      // picks the simulation back up exactly where it left off. But if the
      // server process itself restarted (e.g. a dev --reload, or a real
      // deploy), that session_id is gone for good (code 4404) -- retrying it
      // forever would just loop, so start a fresh session instead.
      socket.onclose = (event) => {
        if (this.socket !== socket) return;
        if (event.code === 4404) {
          window.setTimeout(() => void this.connect(), 1000);
        } else {
          window.setTimeout(() => void this.openSocket(), 1000);
        }
      };
      this.socket = socket;
    });
  }

  async fetchBodies(): Promise<BodyCatalogue> {
    const response = await fetch(`${API_BASE}/api/bodies`);
    return (await response.json()) as BodyCatalogue;
  }

  async fetchOrbitLines(): Promise<OrbitLinesResponse> {
    const response = await fetch(`${API_BASE}/api/orbit_lines`);
    return (await response.json()) as OrbitLinesResponse;
  }

  async fetchMissions(): Promise<MissionCatalogue> {
    const response = await fetch(`${API_BASE}/api/missions`);
    return (await response.json()) as MissionCatalogue;
  }

/** REST menu action: park the craft around a new home body. */
  async setHome(bodyName: string): Promise<{ status: string; home_body?: string }> {
    return this.post("set_home", { body: bodyName });
  }

  /** REST menu action: plan the cheapest Lambert transfer to `target` and launch it. */
  async flyTo(target: string): Promise<{ status: string; mission_label?: string; message?: string }> {
    return this.post("fly_to", { target });
  }

  /** REST menu action: load a historical spacecraft replay or the Earth-Moon trip. */
  async loadMission(name: string): Promise<{ status: string; mission_label?: string }> {
    return this.post("load_mission", { name });
  }

  /** REST menu action: export the current craft's recorded trajectory as CSV. */
  async exportTrajectory(): Promise<{ ok: boolean; text?: string }> {
    const response = await fetch(`${API_BASE}/api/session/${this.sessionId}/export`, {
      method: "POST",
    });
    if (!response.ok) return { ok: false };
    return { ok: true, text: await response.text() };
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${API_BASE}/api/session/${this.sessionId}/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return (await response.json()) as T;
  }

  /** Session id for the REST commands above. */
  get id(): string | null {
    return this.sessionId;
  }

  send(command: Command): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(command));
    }
  }

  /** Ask the server to advance one tick and push a fresh state -- called
   * once per rendered frame, so the sim's speed is tied to time-step choice
   * exactly as it is in the desktop app's per-frame update(). */
  tick(): void {
    this.send({ type: "tick" });
  }
}
