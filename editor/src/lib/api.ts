import type { Job, Library, ProjectData, ProjectSummary, SystemStatus } from "./types";

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
  run: (id: string, stage: "stills" | "full", draft: boolean) => req<Job>("POST", `${P(id)}/run`, { stage, draft }),
  jobs: (id: string) => req<Job[]>("GET", `${P(id)}/jobs`),
  cancel: (jobId: string) => req<Job>("POST", `/api/jobs/${jobId}/cancel`),
  library: () => req<Library>("GET", "/api/library"),
  saveLibrary: (lib: Library) => req<{ ok: true }>("PUT", "/api/library", lib),
};

// URL for a file inside a project folder (rendered stills, audio, final video, imported media).
export const fileUrl = (id: string, rel: string, bust?: string | number) =>
  `${P(id)}/file/${rel.split("/").map(encodeURIComponent).join("/")}${bust ? `?v=${bust}` : ""}`;

export const jobEventsUrl = (jobId: string) => `/api/jobs/${jobId}/events`;
