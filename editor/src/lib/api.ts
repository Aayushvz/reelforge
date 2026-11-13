import type { Job, Library, LocalSettings, ProjectData, ProjectSummary, SystemStatus, VoiceLine } from "./types";
import type { AvCatalog, AvPlan } from "./shotsav";

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body instanceof Blob ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : body instanceof Blob ? body : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { error?: string }).error ?? `${res.status} ${res.statusText}`);
  return data as T;
}

const P = (id: string) => `/api/projects/${encodeURIComponent(id)}`;

export const api = {
  system: () => req<SystemStatus>("GET", "/api/system"),
  projects: () => req<ProjectSummary[]>("GET", "/api/projects"),
  project: (id: string) => req<ProjectData>("GET", P(id)),
  create: (body: { name: string; performance?: unknown; editor?: unknown }) => req<ProjectData>("POST", "/api/projects", body),
  save: (id: string, body: { performance?: unknown; editor?: unknown }) => req<{ savedAt: string }>("PUT", P(id), body),
  duplicate: (id: string) => req<ProjectData>("POST", `${P(id)}/duplicate`),
  remove: (id: string) => req<{ ok: true }>("DELETE", P(id)),
  upload: (id: string, path: string, file: Blob) => req<{ path: string }>("POST", `${P(id)}/upload?path=${encodeURIComponent(path)}`, file),
  run: (id: string, stage: "stills" | "full", draft: boolean, animatic = false, quality?: "standard" | "cinema") =>
    req<Job>("POST", `${P(id)}/run`, { stage, draft, animatic, quality }),
  reveal: (id: string) => req<{ ok: true; path: string }>("POST", `${P(id)}/reveal`),
  avCatalog: () => req<AvCatalog>("GET", "/api/shotsav/catalog"),
  avPlan: (id: string) => req<AvPlan>("POST", `${P(id)}/shotsav/plan`),
  avPreview: (id: string, shot: number, final = false) => req<{ still: string; at: number }>("POST", `${P(id)}/shotsav/preview`, { shot, final }),
  avBuildAssets: () => req<Job>("POST", "/api/shotsav/build-assets"),
  avAssetJob: () => req<Job | null>("GET", "/api/shotsav/build-assets"),
  jobs: (id: string) => req<Job[]>("GET", `${P(id)}/jobs`),
  cancel: (jobId: string) => req<Job>("POST", `/api/jobs/${jobId}/cancel`),
  settings: () => req<LocalSettings>("GET", "/api/settings"),
  saveSettings: (body: { elevenlabsKey?: string | null; elevenlabsModel?: string | null }) => req<LocalSettings>("PUT", "/api/settings", body),
  voices: (id: string) => req<VoiceLine[]>("GET", `${P(id)}/voices`),
  generateVoices: (id: string, lines?: string[], force = false) => req<VoiceLine[]>("POST", `${P(id)}/voices`, { lines, force }),
  library: () => req<Library>("GET", "/api/library"),
  saveLibrary: (lib: Library) => req<{ ok: true }>("PUT", "/api/library", lib),
};

// URL for a file inside a project folder (rendered stills, audio, final video, imported media).
export const fileUrl = (id: string, rel: string, bust?: string | number) =>
  `${P(id)}/file/${rel.split("/").map(encodeURIComponent).join("/")}${bust ? `?v=${bust}` : ""}`;

export const jobEventsUrl = (jobId: string) => `/api/jobs/${jobId}/events`;
export const avThumbUrl = (id: string) => `/api/shotsav/thumbs/${id}.jpg`;
