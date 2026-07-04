// Mirrors server/serialization.py and server/static_data.py exactly --
// single source of truth for both sides' contract (Phase 1 subset).

export interface BodyEntry {
  radius_km: number;
  mass_kg: number;
  color: string;
  rings: number;
  orbital_period_days: number;
  rotation_period_s: number;
  parent_body: string | null;
  texture: string | null;
  is_star: boolean;
}

export type BodyCatalogue = Record<string, BodyEntry>;

export interface Vec3Pair {
  p: [number, number, number];
  v: [number, number, number];
}

export interface HudState {
  time_step_name: string;
  playing: boolean;
  direction: number;
  following: string;
  home_body: string;
  test_drive: boolean;
  mission_label: string;
  notification: string;
}

export interface ShipState {
  p: [number, number, number];
  v: [number, number, number];
  trail_append: [number, number, number][];
  trail_reset: boolean;
}

export interface StateMessage {
  type: "state";
  sim_time_s: number;
  date: string;
  bodies: Record<string, Vec3Pair>;
  ship: ShipState;
  hud: HudState;
  plan: string[];
}

export type TickCommand = { type: "tick" };
export type StepCommand = { type: "step"; direction: number };
export type SetPlayCommand = { type: "set_play"; playing: boolean };
export type ReverseCommand = { type: "reverse" };
export type SetTimeStepCommand = { type: "set_time_step"; index: number };
export type SetFollowCommand = { type: "set_follow"; target: string };
export type ToggleTestDriveCommand = { type: "toggle_test_drive" };

export type Command =
  | TickCommand
  | StepCommand
  | SetPlayCommand
  | ReverseCommand
  | SetTimeStepCommand
  | SetFollowCommand
  | ToggleTestDriveCommand;

export interface OrbitLinesResponse {
  [bodyName: string]: [number, number, number][];
}

export interface MissionEntry {
  description: string;
  color: string;
  follow: string;
}

export type MissionCatalogue = Record<string, MissionEntry>;
