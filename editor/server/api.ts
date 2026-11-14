// Local backend for the editor. Runs inside the Vite dev server as middleware.
// It owns file I/O on project folders and wraps the existing `reelforge` CLI.
// It never touches the pipeline code itself: state lives in each project folder.
import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "node:http";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PROJECT_ROOTS = ["samples", "projects"];
const TRASH = path.join(REPO, "projects", ".trash");
const LIBRARY = path.join(REPO, "projects", "library.json");
const UPLOAD_DIRS = ["out/audio", "media"];
// Local-only secrets (the user's ElevenLabs key). Git-ignored; never logged or sent back whole.
const SETTINGS = path.join(REPO, ".reelforge.local.json");
const ASSETS = path.join(REPO, "assets", "build");
const THUMBS = path.join(ASSETS, "thumbs");
const AV_THUMBS = path.join(ASSETS, "shotsav", "thumbs");
const DEFAULT_MODEL = "eleven_v4";

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
  const perf = readJsonFile<{ ratio?: string; style?: string; lines?: { text: string }[] }>(path.join(dir, "performance.json"));
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
    style: perf?.style ?? "blender3d",
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

// ---------- local settings (API key) ----------

type LocalSettings = { elevenlabsKey?: string; elevenlabsModel?: string };
function readSettings(): LocalSettings { try { return readJsonFile<LocalSettings>(SETTINGS) ?? {}; } catch { return {}; } }
function elevenKey() { return readSettings().elevenlabsKey || process.env.ELEVENLABS_API_KEY || ""; }
function elevenModel() { return readSettings().elevenlabsModel || process.env.ELEVENLABS_MODEL || DEFAULT_MODEL; }
function settingsView() {
  const key = readSettings().elevenlabsKey;
  return {
    elevenlabsKey: Boolean(elevenKey()),
    elevenlabsKeySource: key ? "settings" : process.env.ELEVENLABS_API_KEY ? "environment" : null,
    elevenlabsKeyHint: key ? `…${key.slice(-4)}` : null,
    elevenlabsModel: elevenModel(),
  };
}
function saveSettings(body: { elevenlabsKey?: string | null; elevenlabsModel?: string | null }) {
  const cur = readSettings();
  if (body.elevenlabsKey !== undefined) {
    const k = (body.elevenlabsKey ?? "").trim();
    if (k && !/^[A-Za-z0-9_-]{20,128}$/.test(k)) throw new HttpError(400, "That doesn't look like an ElevenLabs API key.");
    if (k) cur.elevenlabsKey = k; else delete cur.elevenlabsKey;
  }
  if (body.elevenlabsModel !== undefined) {
    const m = (body.elevenlabsModel ?? "").trim();
    if (m && !/^[a-z0-9_]{3,40}$/.test(m)) throw new HttpError(400, "Bad model id");
    if (m) cur.elevenlabsModel = m; else delete cur.elevenlabsModel;
  }
  writeJsonFile(SETTINGS, cur);
  systemCache = null;
  return settingsView();
}

// The pipeline's environment: Blender path plus the user's key, passed only to child processes.
function pipelineEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, ELEVENLABS_MODEL: elevenModel(), PYTHONIOENCODING: "utf-8",
    // piped Python output is block-buffered: without this the Render page sees no live progress
    PYTHONUNBUFFERED: "1",
    // run this checkout's pipeline even when the venv's editable install points at another worktree
    PYTHONPATH: [REPO, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) };
  const blender = blenderPath();
  if (blender) env.REELFORGE_BLENDER = blender;
  const key = elevenKey();
  if (key) env.ELEVENLABS_API_KEY = key; else delete env.ELEVENLABS_API_KEY;
  return env;
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
    elevenlabsKey: Boolean(elevenKey()),
  };
  systemCache = { at: Date.now(), value };
  return value;
}

type Job = {
  id: string; projectId: string; stage: "stills" | "full"; draft: boolean; mode?: "run" | "animatic" | "assets";
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

function startJob(id: string, stage: "stills" | "full", draft: boolean, mode: "run" | "animatic" = "run",
  quality?: "standard" | "cinema"): Job {
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
    projectId: id, stage, draft, mode, status: "running", startedAt: Date.now(), log: [], listeners: new Set(),
  };
  jobs.set(job.id, job);
  const args = mode === "animatic"
    ? ["animatic", dir, "--stage", stage, ...(draft ? [] : ["--final"])]
    : ["run", dir, "--stage", stage, ...(draft ? ["--draft"] : quality ? ["--quality", quality] : [])];
  const proc = spawn(bin, args, { cwd: REPO, env: pipelineEnv() });
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
    const finish = () => {
      broadcast(job, "status", jobView(job));
      for (const res of job.listeners) res.end();
      job.listeners.clear();
    };
    // a finished full render gets a drafted cover (out/cover.json) before the job reports done;
    // best effort: a failed draft never fails the render
    if (job.status === "done" && mode === "run" && stage === "full") {
      draftCover(dir).then(() => job.log.push("Cover drafted: out/cover.json"),
        (e: Error) => job.log.push(`Cover draft skipped: ${e.message}`)).finally(finish);
    } else finish();
  });
  return job;
}

function draftCover(dir: string) {
  return reelforgeJson<Record<string, unknown>>(["cover", dir]);
}

async function getCover(id: string) {
  const dir = projectDir(id);
  const file = path.join(dir, "out", "cover.json");
  const draft = readJsonFile<Record<string, unknown>>(file);
  // redraft when a newer render replaced the video the draft was made for
  const video = draft && typeof draft.video === "string" ? path.join(dir, draft.video) : null;
  if (draft && video && fs.existsSync(video) && fs.statSync(video).mtimeMs <= fs.statSync(file).mtimeMs) return draft;
  const out = path.join(dir, "out");
  if (!fs.existsSync(out) || !fs.readdirSync(out).some((f) => /^final_.*\.mp4$/.test(f))) throw new HttpError(404, "No final video yet");
  return draftCover(dir);
}

// ---------- Shots-AV: catalog, shot plan, preview stills, asset builds, thumbnails ----------

// Run a `reelforge` command that prints one "SHOTSAV_JSON {...}" line; resolve with that JSON.
function reelforgeJson<T>(args: string[]): Promise<T> {
  const bin = reelforgeBin();
  if (!bin) throw new HttpError(409, "The reelforge pipeline isn't installed.");
  return new Promise<T>((resolve, reject) => {
    const proc = spawn(bin, args, { cwd: REPO, env: pipelineEnv() });
    let out = "", tail = "";
    proc.stdout?.on("data", (d: Buffer) => { out += d.toString("utf-8"); });
    proc.stderr?.on("data", (d: Buffer) => { tail = (tail + d.toString("utf-8")).slice(-4000); });
    proc.on("error", reject);
    proc.on("close", (code) => {
      const line = out.split(/\r?\n/).find((l) => l.startsWith("SHOTSAV_JSON "));
      if (code === 0 && line) return resolve(JSON.parse(line.slice("SHOTSAV_JSON ".length)) as T);
      const msg = (tail + "\n" + out).trim().split(/\r?\n/).filter(Boolean).slice(-20).join("\n");
      reject(new HttpError(500, msg || `reelforge exited with code ${code}`));
    });
  });
}

let catalogCache: { at: number; value: unknown } | null = null;
async function shotsavCatalog() {
  if (catalogCache && Date.now() - catalogCache.at < 5_000) return catalogCache.value;
  const value = await reelforgeJson(["shots-av", "catalog"]);
  catalogCache = { at: Date.now(), value };
  return value;
}

// One preview render per project at a time; later requests queue behind it.
const previewQueue = new Map<string, Promise<unknown>>();
function shotsavPreview(id: string, shot: number, final: boolean) {
  const dir = projectDir(id);
  if (!Number.isInteger(shot) || shot < 0) throw new HttpError(400, "Bad shot index");
  const prev = previewQueue.get(id) ?? Promise.resolve();
  const next = prev.catch(() => undefined).then(() =>
    reelforgeJson<{ still: string }>(["shots-av", "preview", dir, "--shot", String(shot), ...(final ? ["--final"] : [])]))
    .then((r) => ({ still: path.relative(dir, r.still).split(path.sep).join("/"), at: Date.now() }));
  previewQueue.set(id, next.finally(() => { if (previewQueue.get(id) === next) previewQueue.delete(id); }));
  return next;
}

// build-assets (hero, buddies, rooms) then the thumbnails, as one job with a live log
function startAssetJob(): Job {
  const running = [...jobs.values()].find((j) => j.projectId === "__shotsav_assets__" && j.status === "running");
  if (running) return running;
  const bin = reelforgeBin();
  if (!bin) throw new HttpError(409, "The reelforge pipeline isn't installed.");
  if (!blenderPath()) throw new HttpError(409, "Blender isn't set up. Put its path in tools/blender_path.txt.");
  const job: Job = {
    id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`, projectId: "__shotsav_assets__",
    stage: "full", draft: false, mode: "assets", status: "running", startedAt: Date.now(), log: [], listeners: new Set(),
  };
  jobs.set(job.id, job);
  const steps = [["build-assets", "--style", "shots-av"], ["thumbnails", "--style", "shots-av"]];
  const runStep = (i: number) => {
    const proc = spawn(bin, steps[i], { cwd: REPO, env: pipelineEnv() });
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
      if (job.status === "running" && code === 0 && i + 1 < steps.length) return runStep(i + 1);
      if (job.status === "running") job.status = code === 0 ? "done" : "failed";
      if (job.status === "failed") job.error = job.log.slice(-20).join("\n") || `Exited with code ${code}`;
      job.endedAt = Date.now();
      catalogCache = null;
      broadcast(job, "status", jobView(job));
      for (const res of job.listeners) res.end();
      job.listeners.clear();
    });
  };
  runStep(0);
  return job;
}

const avThumbJobs = new Map<string, Promise<void>>();
function shotsavThumb(name: string): Promise<string> {
  const m = name.match(/^([a-z0-9_]+)\.jpg$/);
  if (!m) throw new HttpError(400, "Bad thumbnail name");
  const out = path.join(AV_THUMBS, name);
  if (fs.existsSync(out)) return Promise.resolve(out);
  const bin = reelforgeBin();
  if (!bin) throw new HttpError(409, "The reelforge pipeline isn't installed.");
  let job = avThumbJobs.get(m[1]);
  if (!job) {
    job = thumbSlot(() => runProc(bin, ["thumbnails", "--style", "shots-av", "--only", m[1]]))
      .finally(() => avThumbJobs.delete(m[1]));
    avThumbJobs.set(m[1], job);
  }
  return job.then(() => out);
}

function revealFolder(id: string) {
  const dir = projectDir(id);
  const target = fs.existsSync(path.join(dir, "out")) ? path.join(dir, "out") : dir;
  const opener = process.platform === "win32" ? "explorer" : process.platform === "darwin" ? "open" : "xdg-open";
  spawn(opener, [target], { detached: true, stdio: "ignore" }).unref();
  return { ok: true, path: target };
}

// ---------- voices: ElevenLabs takes generated automatically per line ----------

type PerfLineJson = { id: string; speaker: string; text: string; emotion?: string; intensity?: number };
type PerfJson = { style?: string; characters?: Record<string, { voice_id?: string }>; lines?: PerfLineJson[] };
type VoiceRun = { running: boolean; generating: Set<string>; errors: Map<string, { key: string; error: string }>; again: Set<string>; force: boolean };
const voiceRuns = new Map<string, VoiceRun>();
const voiceRun = (id: string) => {
  let r = voiceRuns.get(id);
  if (!r) { r = { running: false, generating: new Set(), errors: new Map(), again: new Set(), force: false }; voiceRuns.set(id, r); }
  return r;
};

// Same name as reelforge/voice.py take_path(): <line>-<sha1(model|voice|text)[:10]>.mp3
// shots-av takes are directed (emotion -> ElevenLabs audio tags), so the delivery is part of the key.
// Mirrors reelforge/voice.py delivery_key(): "<emotion>:<intensity to 2 places>".
function deliveryOf(perf: PerfJson | null, l: PerfLineJson) {
  return perf?.style === "shots-av" ? `${l.emotion ?? "neutral"}:${(l.intensity ?? 0.5).toFixed(2)}` : "";
}

function takeName(lineId: string, voiceId: string, text: string, delivery = "") {
  const tail = delivery ? `|${delivery}` : "";
  return `${lineId}-${crypto.createHash("sha1").update(`${elevenModel()}|${voiceId}|${text}${tail}`, "utf8").digest("hex").slice(0, 10)}.mp3`;
}

function voiceStatus(id: string) {
  const dir = projectDir(id);
  const perf = readJsonFile<PerfJson>(path.join(dir, "performance.json"));
  const audio = path.join(dir, "out", "audio");
  const run = voiceRuns.get(id);
  return (perf?.lines ?? []).map((l) => {
    const take = takeName(l.id, perf?.characters?.[l.speaker]?.voice_id ?? "", l.text, deliveryOf(perf, l));
    if (fs.existsSync(path.join(audio, `${l.id}.mp3`))) return { line: l.id, status: "imported", file: `out/audio/${l.id}.mp3` };
    if (run?.generating.has(l.id)) return { line: l.id, status: "generating" };
    if (fs.existsSync(path.join(audio, take)) && fs.existsSync(path.join(audio, take.replace(/\.mp3$/, ".json")))) {
      return { line: l.id, status: "ready", file: `out/audio/${take}` };
    }
    const err = run?.errors.get(l.id);
    if (err && err.key === take) return { line: l.id, status: "error", error: err.error };
    return { line: l.id, status: l.text.trim() ? "missing" : "empty" };
  });
}

function generateVoices(id: string, lines: string[] | undefined, force: boolean) {
  const dir = projectDir(id);
  const bin = reelforgeBin();
  if (!bin) throw new HttpError(409, "The reelforge pipeline isn't installed.");
  if (!elevenKey()) throw new HttpError(409, "Add your ElevenLabs API key in Settings to generate voices.");
  const run = voiceRun(id);
  const want = voiceStatus(id).filter((s) => (lines ? lines.includes(s.line) : true) &&
    (force ? s.status !== "imported" && s.status !== "empty" : s.status === "missing" || s.status === "error")).map((s) => s.line);
  if (!want.length) return voiceStatus(id);
  want.forEach((l) => { run.generating.add(l); run.errors.delete(l); });
  if (run.running) { want.forEach((l) => run.again.add(l)); run.force ||= force; return voiceStatus(id); }
  run.running = true;
  const perf = readJsonFile<PerfJson>(path.join(dir, "performance.json"));
  const keyOf = (lineId: string) => {
    const l = perf?.lines?.find((x) => x.id === lineId);
    return l ? takeName(l.id, perf?.characters?.[l.speaker]?.voice_id ?? "", l.text, deliveryOf(perf, l)) : "";
  };
  const args = ["voices", dir, ...want.flatMap((l) => ["--line", l]), ...(force ? ["--force"] : [])];
  const proc = spawn(bin, args, { cwd: REPO, env: pipelineEnv() });
  let buf = "", errText = "";
  proc.stdout?.on("data", (d: Buffer) => {
    buf += d.toString("utf-8");
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const raw = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      try {
        const r = JSON.parse(raw) as { line: string; status: string; error?: string };
        if (!run.again.has(r.line)) run.generating.delete(r.line);
        if (r.status === "error") run.errors.set(r.line, { key: keyOf(r.line), error: r.error ?? "Failed" });
      } catch { /* not a status line */ }
    }
  });
  proc.stderr?.on("data", (d: Buffer) => { errText = (errText + d.toString("utf-8")).slice(-2000); });
  const finish = () => {
    if (!run.running) return;
    // anything still marked generating crashed before reporting (bad script, unknown speaker...)
    const msg = errText.trim().split(/\r?\n/).filter(Boolean).pop() ?? "Voice generation stopped";
    for (const l of want) if (run.generating.has(l) && !run.again.has(l)) { run.generating.delete(l); run.errors.set(l, { key: keyOf(l), error: msg }); }
    run.running = false;
    if (run.again.size) {
      const next = [...run.again], f = run.force;
      run.again.clear(); run.force = false; next.forEach((l) => run.generating.delete(l));
      try { generateVoices(id, next, f); } catch { /* key removed meanwhile */ }
    }
  };
  proc.on("close", finish);
  proc.on("error", (e) => { errText += e.message; finish(); });
  return voiceStatus(id);
}

// ---------- asset thumbnails: real Blender renders of the built cast and sets, cached on disk ----------

const thumbJobs = new Map<string, Promise<string>>();
let thumbActive = 0;
const thumbWaiters: (() => void)[] = [];
async function thumbSlot<T>(fn: () => Promise<T>): Promise<T> {
  while (thumbActive >= 2) await new Promise<void>((r) => thumbWaiters.push(r));
  thumbActive++;
  try { return await fn(); } finally { thumbActive--; thumbWaiters.shift()?.(); }
}

function runProc(cmd: string, args: string[]) {
  return new Promise<void>((resolve, reject) => {
    const p = spawn(cmd, args, { cwd: REPO, stdio: ["ignore", "ignore", "pipe"] });
    let err = "";
    p.stderr?.on("data", (d: Buffer) => { err = (err + d.toString()).slice(-800); });
    p.on("error", reject);
    p.on("close", (code) => code === 0 ? resolve() : reject(new Error(err.trim().split(/\r?\n/).pop() || `exit ${code}`)));
  });
}

function thumbFor(kind: string, a: string, b: string): Promise<string> {
  if (!/^[a-z0-9_]+$/.test(a) || !/^[a-z0-9_]+$/.test(b)) throw new HttpError(400, "Bad asset id");
  const name = kind === "character" ? `char_${a}_o${b}.jpg` : kind === "set" ? `set_${a}__${b}.jpg` : null;
  if (!name) throw new HttpError(404, "Unknown thumbnail kind");
  const out = path.join(THUMBS, name);
  if (fs.existsSync(out)) return Promise.resolve(out);
  const pending = thumbJobs.get(name);
  if (pending) return pending;
  const blender = blenderPath();
  if (!blender) throw new HttpError(409, "Blender isn't set up");
  const png = path.join(THUMBS, `.${name}.png`);
  const blend = path.join(ASSETS, kind === "character" ? (b === "0" ? `${a}.blend` : `${a}__o${b}.blend`) : `${a}__${b}.blend`);
  if (!fs.existsSync(blend)) throw new HttpError(404, `Not built yet: ${path.basename(blend)}. Run reelforge build-assets.`);
  const args = kind === "character"
    ? ["-b", blend, "-P", path.join(REPO, "blender", "preview_character.py"), "--", png, "yaw=20", "shot=bust"]
    : ["-b", blend, "-P", path.join(REPO, "blender", "preview_set.py"), "--", png, path.join(ASSETS, "matt.blend"), "wide"];
  fs.mkdirSync(THUMBS, { recursive: true });
  const job = thumbSlot(async () => {
    await runProc(blender, args);
    await runProc("ffmpeg", ["-v", "error", "-y", "-i", png, "-vf", "scale=480:-2", "-q:v", "4", out]);
    fs.rmSync(png, { force: true });
    return out;
  }).finally(() => thumbJobs.delete(name));
  thumbJobs.set(name, job);
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
  if (head === "settings") {
    if (method === "GET") return send(res, 200, settingsView());
    if (method === "PUT") return send(res, 200, saveSettings(await readJson(req)));
  }
  if (head === "shotsav") {
    if (id === "catalog" && method === "GET") return send(res, 200, await shotsavCatalog());
    if (id === "build-assets" && method === "POST") return send(res, 202, jobView(startAssetJob()));
    if (id === "build-assets" && method === "GET") {
      const j = [...jobs.values()].filter((x) => x.projectId === "__shotsav_assets__").pop();
      return send(res, 200, j ? jobView(j) : null);
    }
    if (id === "thumbs" && action && method === "GET") {
      const job = shotsavThumb(action);
      const done = await Promise.race([job, new Promise<null>((r) => setTimeout(() => r(null), 50))]).catch(() => null);
      if (!done) {
        job.catch(() => undefined);
        res.setHeader("Retry-After", "3");
        return send(res, 503, { pending: true });
      }
      res.setHeader("Cache-Control", "max-age=600");
      return serveFile(req, res, done);
    }
  }

  if (head === "thumbs" && method === "GET" && id && action && rest[0]) {
    // Never hold the request while Blender renders: browsers allow ~6 connections per host,
    // and parked thumbnail requests would stall saves. Answer 503 and let the image retry.
    const job = thumbFor(id, action, rest[0].replace(/\.jpg$/, ""));
    const done = await Promise.race([job, new Promise<null>((r) => setTimeout(() => r(null), 50))]).catch(() => null);
    if (!done) {
      job.catch(() => undefined);
      res.setHeader("Retry-After", "3");
      return send(res, 503, { pending: true });
    }
    res.setHeader("Cache-Control", "max-age=3600");
    return serveFile(req, res, done);
  }

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
      const body = await readJson<{ stage?: "stills" | "full"; draft?: boolean; animatic?: boolean; quality?: string }>(req);
      const quality = body.quality === "cinema" || body.quality === "standard" ? body.quality : undefined;
      return send(res, 202, jobView(startJob(id, body.stage === "full" ? "full" : "stills", Boolean(body.draft),
        body.animatic ? "animatic" : "run", quality)));
    }
    if (id && action === "shotsav" && rest[0] === "plan" && method === "POST") {
      projectDir(id);
      return send(res, 200, await reelforgeJson(["shots-av", "plan", projectDir(id)]));
    }
    if (id && action === "shotsav" && rest[0] === "preview" && method === "POST") {
      const body = await readJson<{ shot?: number; final?: boolean }>(req);
      return send(res, 200, await shotsavPreview(id, Number(body.shot), Boolean(body.final)));
    }
    if (id && action === "cover" && method === "GET") return send(res, 200, await getCover(id));
    if (id && action === "reveal" && method === "POST") return send(res, 200, revealFolder(id));
    if (id && action === "voices") {
      if (method === "GET") return send(res, 200, voiceStatus(id));
      if (method === "POST") {
        const body = await readJson<{ lines?: string[]; force?: boolean }>(req);
        return send(res, 202, generateVoices(id, Array.isArray(body.lines) ? body.lines : undefined, Boolean(body.force)));
      }
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
