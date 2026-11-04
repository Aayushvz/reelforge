// Local backend for the editor. Runs inside the Vite dev server as middleware.
// It owns file I/O on project folders and wraps the existing `reelforge` CLI.
// It never touches the pipeline code itself: state lives in each project folder.
import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "node:http";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PROJECT_ROOTS = ["samples", "projects"];
const TRASH = path.join(REPO, "projects", ".trash");
const LIBRARY = path.join(REPO, "projects", "library.json");
const UPLOAD_DIRS = ["out/audio", "media"];

const MIME: Record<string, string> = {
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
  ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
  ".json": "application/json", ".ass": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
};

class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

// ---------- helpers ----------

function send(res: ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(body));
}

function readBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

async function readJson<T>(req: IncomingMessage): Promise<T> {
  const buf = await readBody(req);
  try { return JSON.parse(buf.toString("utf-8") || "{}") as T; }
  catch { throw new HttpError(400, "Body is not valid JSON"); }
}

function readJsonFile<T>(file: string): T | null {
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf-8")) as T;
}

function writeJsonFile(file: string, data: unknown) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n", "utf-8");
}

function slugify(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "untitled";
}

function idFor(rel: string) { return rel.replace(/\//g, "~"); }

function projectDir(id: string) {
  const rel = id.replace(/~/g, "/");
  const [root, name, ...rest] = rel.split("/");
  if (!PROJECT_ROOTS.includes(root) || !name || rest.length || name.startsWith(".")) {
    throw new HttpError(400, `Bad project id: ${id}`);
  }
  const dir = path.join(REPO, root, name);
  if (!fs.existsSync(dir)) throw new HttpError(404, `Project not found: ${id}`);
  return dir;
}

// Resolve a path inside a project and refuse anything that escapes it.
function insideProject(dir: string, rel: string) {
  const full = path.resolve(dir, rel);
  if (!full.startsWith(dir + path.sep)) throw new HttpError(400, "Path escapes project");
  return full;
}

function listFiles(dir: string, exts: string[]) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => exts.includes(path.extname(f).toLowerCase())).sort();
}

function uniqueDir(root: string, base: string) {
  let name = base;
  for (let i = 2; fs.existsSync(path.join(REPO, root, name)); i++) name = `${base}-${i}`;
  return name;
}

// ---------- project model ----------

type EditorDoc = Record<string, unknown> & {
  name?: string; kind?: string; archived?: boolean; updatedAt?: string; createdAt?: string;
  history?: unknown[];
};

function projectFiles(dir: string) {
  const out = path.join(dir, "out");
  const finals = listFiles(out, [".mp4"]).filter((f) => f.startsWith("final_"));
  return {
    audio: listFiles(path.join(out, "audio"), [".mp3", ".wav", ".m4a"]),
    stills: listFiles(path.join(out, "stills"), [".png", ".jpg"]),
    media: listFiles(path.join(dir, "media"), [".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".png", ".jpg", ".jpeg", ".webp"]),
    finals,
    dialogue: fs.existsSync(path.join(out, "dialogue.wav")),
    renderPlan: fs.existsSync(path.join(out, "render_plan.json")),
    captions: fs.existsSync(path.join(out, "captions.ass")),
  };
}

function summary(root: string, name: string) {
  const dir = path.join(REPO, root, name);
  const perf = readJsonFile<{ ratio?: string; lines?: { text: string }[] }>(path.join(dir, "performance.json"));
  const ed = readJsonFile<EditorDoc>(path.join(dir, "editor.json")) ?? {};
  const files = projectFiles(dir);
  const stat = fs.statSync(dir);
  const mtimes = ["performance.json", "editor.json"]
    .map((f) => path.join(dir, f)).filter(fs.existsSync).map((f) => fs.statSync(f).mtimeMs);
  const status = files.finals.length ? "rendered" : files.stills.length ? "stills" : "draft";
  return {
    id: idFor(`${root}/${name}`),
    folder: `${root}/${name}`,
    name: ed.name ?? name,
    kind: ed.kind ?? (perf ? "generated" : "blank"),
    archived: Boolean(ed.archived),
    status,
    ratio: (ed.output as { ratio?: string } | undefined)?.ratio ?? perf?.ratio ?? "9:16",
    lineCount: perf?.lines?.length ?? 0,
    words: perf?.lines?.reduce((n, l) => n + l.text.replace(/\[[^\]]*\]/g, "").split(/\s+/).filter(Boolean).length, 0) ?? 0,
    updatedAt: new Date(Math.max(stat.mtimeMs, ...mtimes)).toISOString(),
    thumb: files.stills[0] ? `out/stills/${files.stills[0]}` : null,
    final: files.finals[0] ? `out/${files.finals[0]}` : null,
  };
}

function listProjects() {
  const all = [];
  for (const root of PROJECT_ROOTS) {
    const base = path.join(REPO, root);
    if (!fs.existsSync(base)) continue;
    for (const name of fs.readdirSync(base)) {
      if (name.startsWith(".")) continue;
      const dir = path.join(base, name);
      if (!fs.statSync(dir).isDirectory()) continue;
      if (!fs.existsSync(path.join(dir, "performance.json")) && !fs.existsSync(path.join(dir, "editor.json"))) continue;
      all.push(summary(root, name));
    }
  }
  return all.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

function getProject(id: string) {
  const dir = projectDir(id);
  const [root, name] = id.split("~");
  return {
    ...summary(root, name),
    performance: readJsonFile(path.join(dir, "performance.json")),
    editor: readJsonFile(path.join(dir, "editor.json")) ?? {},
    files: projectFiles(dir),
  };
}

function createProject(body: { name?: string; performance?: unknown; editor?: EditorDoc }) {
  const name = (body.name ?? "Untitled reel").trim() || "Untitled reel";
  const folder = uniqueDir("projects", slugify(name));
  const dir = path.join(REPO, "projects", folder);
  fs.mkdirSync(dir, { recursive: true });
  const now = new Date().toISOString();
  if (body.performance) writeJsonFile(path.join(dir, "performance.json"), body.performance);
  writeJsonFile(path.join(dir, "editor.json"), { ...(body.editor ?? {}), name, createdAt: now, updatedAt: now });
  return getProject(idFor(`projects/${folder}`));
}

function saveProject(id: string, body: { performance?: unknown; editor?: EditorDoc }) {
  const dir = projectDir(id);
  if (body.performance !== undefined) writeJsonFile(path.join(dir, "performance.json"), body.performance);
  if (body.editor !== undefined) writeJsonFile(path.join(dir, "editor.json"), { ...body.editor, updatedAt: new Date().toISOString() });
  return { ok: true, savedAt: new Date().toISOString() };
}

function patchEditor(dir: string, patch: (ed: EditorDoc) => EditorDoc) {
  const file = path.join(dir, "editor.json");
  writeJsonFile(file, { ...patch(readJsonFile<EditorDoc>(file) ?? {}), updatedAt: new Date().toISOString() });
}

function duplicateProject(id: string) {
  const src = projectDir(id);
  const ed = readJsonFile<EditorDoc>(path.join(src, "editor.json")) ?? {};
  const name = `${ed.name ?? path.basename(src)} copy`;
  const folder = uniqueDir("projects", slugify(name));
  const dest = path.join(REPO, "projects", folder);
  // Copy the project's own files and inputs; rendered output is not duplicated.
  fs.cpSync(src, dest, { recursive: true, filter: (p) => !p.includes(`${path.sep}out${path.sep}frames`) });
  patchEditor(dest, (e) => ({ ...e, name, createdAt: new Date().toISOString(), history: [] }));
  return getProject(idFor(`projects/${folder}`));
}

function trashProject(id: string) {
  if (id.startsWith("samples~")) throw new HttpError(403, "Sample projects are part of the repo and can't be deleted here.");
  const dir = projectDir(id);
  fs.mkdirSync(TRASH, { recursive: true });
  fs.renameSync(dir, path.join(TRASH, `${path.basename(dir)}-${Date.now()}`));
  return { ok: true };
}

// ---------- system + pipeline ----------

function reelforgeBin() {
  const win = path.join(REPO, ".venv", "Scripts", "reelforge.exe");
  const nix = path.join(REPO, ".venv", "bin", "reelforge");
  return fs.existsSync(win) ? win : fs.existsSync(nix) ? nix : null;
}

function blenderPath() {
  const file = path.join(REPO, "tools", "blender_path.txt");
  if (!fs.existsSync(file)) return null;
  const p = fs.readFileSync(file, "utf-8").trim();
  return p && fs.existsSync(p) ? p : null;
}

function onPath(cmd: string) {
  try { return spawnSync(cmd, ["-version"], { stdio: "ignore" }).status === 0; } catch { return false; }
}

let systemCache: { at: number; value: unknown } | null = null;
function systemStatus() {
  if (systemCache && Date.now() - systemCache.at < 10_000) return systemCache.value;
  const value = {
    repo: REPO,
    reelforge: Boolean(reelforgeBin()),
    blender: Boolean(blenderPath()),
    ffmpeg: onPath("ffmpeg"),
    assetsBuilt: fs.existsSync(path.join(REPO, "assets", "build", "kai.blend")),
    elevenlabsKey: Boolean(process.env.ELEVENLABS_API_KEY),
  };
  systemCache = { at: Date.now(), value };
  return value;
}

type Job = {
  id: string; projectId: string; stage: "stills" | "full"; draft: boolean;
  status: "running" | "done" | "failed" | "cancelled"; startedAt: number; endedAt?: number;
  log: string[]; proc?: ChildProcess; listeners: Set<ServerResponse>; error?: string;
};
const jobs = new Map<string, Job>();

function broadcast(job: Job, event: string, data: unknown) {
  for (const res of job.listeners) res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

function jobView(job: Job) {
  const { proc: _p, listeners: _l, ...rest } = job;
  return rest;
}

function startJob(id: string, stage: "stills" | "full", draft: boolean): Job {
  const dir = projectDir(id);
  const running = [...jobs.values()].find((j) => j.projectId === id && j.status === "running");
  if (running) return running;
  const bin = reelforgeBin();
  const blender = blenderPath();
  if (!bin) throw new HttpError(409, "The reelforge pipeline isn't installed. Create .venv and run pip install -e \".[dev,align]\" in the repo.");
  if (!blender) throw new HttpError(409, "Blender isn't set up. Put Blender 4.5 in tools/blender-4.5/ and its path in tools/blender_path.txt.");
  if (!fs.existsSync(path.join(dir, "performance.json"))) throw new HttpError(409, "This project has no script yet.");

  const job: Job = {
    id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    projectId: id, stage, draft, status: "running", startedAt: Date.now(), log: [], listeners: new Set(),
  };
  jobs.set(job.id, job);
  const args = ["run", dir, "--stage", stage, ...(draft ? ["--draft"] : [])];
  const proc = spawn(bin, args, { cwd: REPO, env: { ...process.env, REELFORGE_BLENDER: blender } });
  job.proc = proc;
  const onData = (buf: Buffer) => {
    for (const line of buf.toString("utf-8").split(/\r?\n/)) {
      if (!line.trim()) continue;
      job.log.push(line);
      if (job.log.length > 2000) job.log.shift();
      broadcast(job, "log", line);
    }
  };
  proc.stdout?.on("data", onData);
  proc.stderr?.on("data", onData);
  proc.on("close", (code) => {
    if (job.status === "running") job.status = code === 0 ? "done" : "failed";
    if (job.status === "failed") job.error = job.log.slice(-6).join("\n") || `Exited with code ${code}`;
    job.endedAt = Date.now();
    patchEditor(dir, (ed) => ({
      ...ed,
      history: [...(Array.isArray(ed.history) ? ed.history : []),
        { at: new Date(job.startedAt).toISOString(), stage, draft, status: job.status, ms: job.endedAt! - job.startedAt }].slice(-50),
    }));
    broadcast(job, "status", jobView(job));
    for (const res of job.listeners) res.end();
    job.listeners.clear();
  });
  return job;
}

// ---------- file serving with range support (video scrubbing needs it) ----------

function serveFile(req: IncomingMessage, res: ServerResponse, file: string) {
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) throw new HttpError(404, "File not found");
  const size = fs.statSync(file).size;
  const type = MIME[path.extname(file).toLowerCase()] ?? "application/octet-stream";
  res.setHeader("Content-Type", type);
  res.setHeader("Accept-Ranges", "bytes");
  res.setHeader("Cache-Control", "no-cache");
  const range = req.headers.range?.match(/bytes=(\d*)-(\d*)/);
  if (range) {
    const start = range[1] ? Number(range[1]) : 0;
    const end = range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    res.statusCode = 206;
    res.setHeader("Content-Range", `bytes ${start}-${end}/${size}`);
    res.setHeader("Content-Length", end - start + 1);
    fs.createReadStream(file, { start, end }).pipe(res);
    return;
  }
  res.setHeader("Content-Length", size);
  if (req.method === "HEAD") { res.end(); return; }
  fs.createReadStream(file).pipe(res);
}

// ---------- router ----------

async function handle(req: IncomingMessage, res: ServerResponse) {
  const url = new URL(req.url ?? "/", "http://localhost");
  const parts = url.pathname.replace(/^\/api\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const method = req.method ?? "GET";
  const [head, id, action, ...rest] = parts;

  if (head === "system" && method === "GET") return send(res, 200, systemStatus());

  if (head === "library") {
    if (method === "GET") return send(res, 200, readJsonFile(LIBRARY) ?? {});
    if (method === "PUT") { writeJsonFile(LIBRARY, await readJson(req)); return send(res, 200, { ok: true }); }
  }

  if (head === "projects") {
    if (!id) {
      if (method === "GET") return send(res, 200, listProjects());
      if (method === "POST") return send(res, 201, createProject(await readJson(req)));
    }
    if (id && !action) {
      if (method === "GET") return send(res, 200, getProject(id));
      if (method === "PUT") return send(res, 200, saveProject(id, await readJson(req)));
      if (method === "DELETE") return send(res, 200, trashProject(id));
    }
    if (id && action === "duplicate" && method === "POST") return send(res, 201, duplicateProject(id));
    if (id && action === "file" && (method === "GET" || method === "HEAD")) return serveFile(req, res, insideProject(projectDir(id), rest.join("/")));
    if (id && action === "upload" && method === "POST") {
      const dir = projectDir(id);
      const file = insideProject(dir, url.searchParams.get("path") ?? "");
      // the resolved path must land inside one of the upload folders, not just start with its name
      if (!UPLOAD_DIRS.some((d) => file.startsWith(path.join(dir, d) + path.sep))) throw new HttpError(400, `Uploads go to ${UPLOAD_DIRS.join(" or ")}`);
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, await readBody(req));
      return send(res, 201, { ok: true, path: path.relative(dir, file).split(path.sep).join("/") });
    }
    if (id && action === "run" && method === "POST") {
      const body = await readJson<{ stage?: "stills" | "full"; draft?: boolean }>(req);
      return send(res, 202, jobView(startJob(id, body.stage === "full" ? "full" : "stills", Boolean(body.draft))));
    }
    if (id && action === "jobs" && method === "GET") {
      return send(res, 200, [...jobs.values()].filter((j) => j.projectId === id).map(jobView));
    }
  }

  if (head === "jobs" && id) {
    const job = jobs.get(id);
    if (!job) throw new HttpError(404, "Job not found");
    if (action === "events" && method === "GET") {
      res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
      res.write(`event: status\ndata: ${JSON.stringify(jobView(job))}\n\n`);
      if (job.status !== "running") return res.end();
      job.listeners.add(res);
      req.on("close", () => job.listeners.delete(res));
      return;
    }
    if (action === "cancel" && method === "POST") {
      if (job.status === "running") { job.status = "cancelled"; job.proc?.kill(); }
      return send(res, 200, jobView(job));
    }
  }

  throw new HttpError(404, `No route for ${method} ${url.pathname}`);
}

export function reelforgeApi(): Plugin {
  return {
    name: "reelforge-api",
    configureServer(server) {
      server.middlewares.use("/api", (req, res) => {
        req.url = "/api" + (req.url ?? "");
        handle(req, res).catch((err: unknown) => {
          const status = err instanceof HttpError ? err.status : 500;
          send(res, status, { error: err instanceof Error ? err.message : String(err) });
        });
      });
    },
  };
}
