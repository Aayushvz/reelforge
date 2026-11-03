import { create } from "zustand";
import { api } from "@/lib/api";
import type { SystemStatus } from "@/lib/types";

export const useSystem = create<{ status: SystemStatus | null; load: () => Promise<void> }>((set) => ({
  status: null,
  async load() { try { set({ status: await api.system() }); } catch { /* shown as unknown */ } },
}));

export const pipelineReady = (s: SystemStatus | null) => Boolean(s?.reelforge && s.blender && s.ffmpeg);
