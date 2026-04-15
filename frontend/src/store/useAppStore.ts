import { create } from "zustand";
import type { Config, Stats } from "../lib/api";

type Status = "playing" | "paused" | "stopped";

type State = {
  stats: Stats;
  config: Config;
  status: Status;
  streamKey: number;
  wsConnected: boolean;
  setStats: (s: Stats) => void;
  setConfig: (c: Config) => void;
  setStatus: (s: Status) => void;
  bumpStream: () => void;
  setWsConnected: (b: boolean) => void;
};

export const useAppStore = create<State>((set) => ({
  stats: { frame_id: 0, people: 0, unsafe: 0, fps: 0, error: null, paused: false },
  config: { safe_distance: 75, conf_threshold: 0.5 },
  status: "playing",
  streamKey: Date.now(),
  wsConnected: false,
  setStats: (stats) => set({ stats }),
  setConfig: (config) => set({ config }),
  setStatus: (status) => set({ status }),
  bumpStream: () => set({ streamKey: Date.now() }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
}));
