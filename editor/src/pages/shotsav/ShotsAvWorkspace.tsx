// Shots-AV workspace: Script (left) · Stage with the shot strip (centre) · Look (right).
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent as RKeyboardEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Camera, ClipboardPaste, Eye, Film, FolderOpen, MoreHorizontal, Plus, RefreshCw, Trash2,
  Wand2, X, Music, AudioLines, Hammer, Sparkles, Settings as SettingsIcon, Captions as CaptionsIcon, Dices,
} from "lucide-react";
import { api, avThumbUrl, fileUrl, jobEventsUrl } from "@/lib/api";
import type { Emotion, Job, Performance, PerfLine, ProjectData, SubtitleStyle, SystemStatus, VoiceLine } from "@/lib/types";
import { SubtitleCard, SubtitleControls, SubtitleGrid } from "@/components/pickers";
import { CHARACTERS, SUBTITLE_TEMPLATES, VOICES } from "@/data/catalog";
import { EMOTIONS } from "@/lib/types";
import {
  ACTION_LABEL, BUDDY, HERO, MOVES, MOVE_LABEL, PURPLE, SETUP_LABEL, STARTERS, estimateRuntime, fmtDur, fmtSec,
  label, makeLine, parseScript, renumber, type AvCatalog, type AvPlan, type AvSetup,
  BUDDY_VOICE, HERO_VOICE, SHOTSAV_TOP_ID, SHOTSAV_TOP_STYLE, parseRgba, toRgba,
  AV_HERO, PEOPLE, PERSON_ACCENT, isBot, isPerson,
} from "@/lib/shotsav";
import { Badge, Callout, Empty, Spinner } from "@/components/ui/Feedback";
import { Dialog, Tooltip, useMenu } from "@/components/ui/Overlay";
import { ColorInput, FieldRow, IconButton, Section, Segmented, Select, Slider, Switch } from "@/components/ui/Form";
import { toast } from "@/stores/ui";
import { useProject } from "@/stores/project";
import { CaptionPlacer, RoomFramePicker } from "./Placers";
import "./shotsav.css";

type Tab = "script" | "stage" | "look";
type Live = { job: Job | null; log: string[]; frame: number };

const mins = (sec: number) => `${Math.max(1, Math.round(sec / 60))}m`;
const ROLE_SHORT = { hero: "You", buddy: "Buddy", wide: "Wide" } as const;
const roleOf = (kind: string): "hero" | "buddy" | "wide" => (kind === "av_buddy" ? "buddy" : kind.startsWith("av_wide") ? "wide" : "hero");

const personName = (model: string) => CHARACTERS.find((c) => c.id === model)?.name ?? model;
const personVoice = (model: string) => {
  const c = CHARACTERS.find((x) => x.id === model);
  return VOICES.find((v) => v.name === c?.suggestedVoice)?.id ?? HERO_VOICE;
};
const defaultVoice = (model: string) => (model === AV_HERO ? HERO_VOICE : isBot(model) ? BUDDY_VOICE[model] : personVoice(model));

function AvThumb({ id, alt }: { id: string; alt: string }) {
  const [tries, setTries] = useState(0);
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    if (ok !== false || tries > 30) return;
    const t = setTimeout(() => { setOk(null); setTries((n) => n + 1); }, 3000);
    return () => clearTimeout(t);
  }, [ok, tries]);
  return (
    <span className="av-thumb">
      {ok !== true && <span className="av-thumb-wait">{ok === false ? <Spinner /> : null}</span>}
      <img src={tries ? `${avThumbUrl(id)}?r=${tries}` : avThumbUrl(id)} alt={alt} draggable={false}
        style={{ opacity: ok ? 1 : 0 }} onLoad={() => setOk(true)} onError={() => setOk(false)} />
    </span>
  );
}

export function ShotsAvWorkspace() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState<ProjectData | null>(null);
  const [perf, setPerf] = useState<Performance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cat, setCat] = useState<AvCatalog | null>(null);
  const [catError, setCatError] = useState<string | null>(null);
  const [plan, setPlan] = useState<AvPlan | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [voices, setVoices] = useState<Record<string, VoiceLine>>({});
  const [sel, setSel] = useState(0);
  const [preview, setPreview] = useState<{ shot: number; url: string } | null>(null);
  const [previewing, setPreviewing] = useState<number | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [look, setLook] = useState<string | null>(null);  // the look still: cast and outfit in the room
  const [lookBusy, setLookBusy] = useState(false);
  const [lookError, setLookError] = useState<string | null>(null);
  const [showLook, setShowLook] = useState(true);  // the stage shows the look until a shot is previewed
  const lookSeq = useRef(0);
  const [live, setLive] = useState<Live>({ job: null, log: [], frame: 0 });
  const [assets, setAssets] = useState<Live>({ job: null, log: [], frame: 0 });
  const [tab, setTab] = useState<Tab>("script");
  const [paste, setPaste] = useState(false);
  const [saved, setSaved] = useState<"saved" | "saving" | "error">("saved");
  const [sys, setSys] = useState<SystemStatus | null>(null);
  const [quality, setQuality] = useState<"draft" | "balanced" | "final">("balanced");
  const [gen, setGen] = useState<{ phase: "idle" | "voices" | "render" | "error"; done?: number; total?: number; error?: string }>({ phase: "idle" });
  const [subsOpen, setSubsOpen] = useState(false);
  const focusLine = useRef<number | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout>>();
  const menu = useMenu();

  // ---------- load ----------
  const load = useCallback(async () => {
    try {
      const p = await api.project(id);
      let perfIn = p.performance;
      if (perfIn?.style === "shots-av") {  // older desk reels saved no voices: cast the defaults once
        const me = perfIn.characters[HERO], bud = perfIn.characters[BUDDY];
        if (me && bud && (!me.voice_id || !bud.voice_id)) {
          perfIn = { ...perfIn, characters: { ...perfIn.characters,
            [HERO]: { ...me, voice_id: me.voice_id || HERO_VOICE },
            [BUDDY]: { ...bud, voice_id: bud.voice_id || BUDDY_VOICE[bud.model ?? ""] || BUDDY_VOICE.buddy_claude } } };
          await api.save(id, { performance: perfIn });
        }
      }
      setData(p);
      setPerf(perfIn);
      setError(null);
    } catch (e) { setError((e as Error).message); }
  }, [id]);
  const loadCatalog = useCallback(() => {
    setCatError(null);
    api.avCatalog().then(setCat).catch((e) => setCatError((e as Error).message));
  }, []);
  const loadVoices = useCallback(() => {
    api.voices(id).then((v) => setVoices(Object.fromEntries(v.map((x) => [x.line, x])))).catch(() => undefined);
  }, [id]);
  const refreshPlan = useCallback(() => {
    api.avPlan(id).then((p) => { setPlan(p); setPlanError(null); }).catch((e) => setPlanError((e as Error).message));
  }, [id]);
  useEffect(() => { void load(); loadCatalog(); loadVoices(); api.system().then(setSys).catch(() => undefined); }, [load, loadCatalog, loadVoices]);
  useEffect(() => { if (perf?.lines.length) refreshPlan(); }, [data, refreshPlan]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {  // pick up a job that is still running (page reload)
    api.jobs(id).then((js) => { const r = js.find((j) => j.status === "running"); if (r) follow(r, setLive); }).catch(() => undefined);
    api.avAssetJob().then((j) => { if (j && j.status === "running") follow(j, setAssets); }).catch(() => undefined);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------- save (debounced); the plan follows the saved file ----------
  const update = useCallback((fn: (p: Performance) => Performance) => {
    setPerf((cur) => {
      if (!cur) return cur;
      const next = fn(cur);
      clearTimeout(saveTimer.current);
      setSaved("saving");
      saveTimer.current = setTimeout(() => {
        api.save(id, { performance: next }).then(() => { setSaved("saved"); refreshPlan(); loadVoices(); })
          .catch((e) => { setSaved("error"); toast(`Couldn't save: ${(e as Error).message}`, "err"); });
      }, 600);
      return next;
    });
  }, [id, refreshPlan, loadVoices]);
  const flush = useCallback(async () => {
    if (saveTimer.current && perf) { clearTimeout(saveTimer.current); saveTimer.current = undefined; await api.save(id, { performance: perf }); setSaved("saved"); }
  }, [id, perf]);

  // ---------- jobs ----------
  function follow(job: Job, set: typeof setLive) {
    set({ job, log: job.log ?? [], frame: 0 });
    const es = new EventSource(jobEventsUrl(job.id));
    es.addEventListener("log", (e) => {
      const line = JSON.parse((e as MessageEvent).data) as string;
      const fra = line.match(/Fra:\s*(\d+)/);
      set((s) => ({ ...s, log: [...s.log.slice(-400), line], frame: fra ? Number(fra[1]) : s.frame }));
    });
    es.addEventListener("status", (e) => {
      const j = JSON.parse((e as MessageEvent).data) as Job;
      set((s) => ({ ...s, job: j }));
      if (j.status !== "running") { es.close(); void load(); loadCatalog(); }
    });
    es.onerror = () => es.close();
  }
  const start = async (kind: "animatic" | "draft" | "balanced" | "final") => {
    try {
      await flush();
      const job = kind === "animatic" ? await api.run(id, "full", true, true)
        : await api.run(id, "full", kind === "draft", false, kind === "final" ? "cinema" : "standard");
      follow(job, setLive);
      setTab("stage");
    } catch (e) { toast((e as Error).message, "err"); }
  };
  // Script -> ElevenLabs voices (each line's emotion performed) -> the video, timed to the real audio.
  const generateReel = async () => {
    try {
      await flush();
      const ready = (v?: VoiceLine) => v?.status === "imported" || v?.status === "ready";
      let status = Object.fromEntries((await api.voices(id)).map((x) => [x.line, x]));
      const need = lines.filter((l) => !ready(status[l.id]));
      if (need.length) {
        if (!sys?.elevenlabsKey) {
          setGen({ phase: "error", error: "Add your ElevenLabs API key in Settings, then press Generate reel again." });
          return;
        }
        setGen({ phase: "voices", done: lines.length - need.length, total: lines.length });
        await api.generateVoices(id);
        const t0 = Date.now();
        for (;;) {
          await new Promise((r) => setTimeout(r, 2000));
          const list = await api.voices(id);
          status = Object.fromEntries(list.map((x) => [x.line, x]));
          setVoices(status);
          const done = lines.filter((l) => ready(status[l.id])).length;
          setGen({ phase: "voices", done, total: lines.length });
          const failed = list.filter((x) => x.status === "error");
          if (failed.length) {
            setGen({ phase: "error", error: failed.map((x) => `${x.line}: ${x.error}`).join("\n") });
            return;
          }
          if (done === lines.length) break;
          if (!list.some((x) => x.status === "generating") || Date.now() - t0 > 10 * 60_000) {
            setGen({ phase: "error", error: "Voice generation stopped before every line had a take. Press Generate reel to try again." });
            return;
          }
        }
      }
      setGen({ phase: "render" });
      await start(quality);
      setGen({ phase: "idle" });
    } catch (e) { setGen({ phase: "error", error: (e as Error).message }); }
  };
  const buildAssets = async () => {
    try { follow(await api.avBuildAssets(), setAssets); } catch (e) { toast((e as Error).message, "err"); }
  };
  const runPreview = useCallback(async (shot: number) => {
    if (!plan || !plan.shots[shot]) return;
    setSel(shot);
    setShowLook(false);
    setPreviewing(shot);
    setPreviewError(null);
    try {
      await flush();
      const r = await api.avPreview(id, shot);
      setPreview({ shot, url: fileUrl(id, r.still, r.at) });
    } catch (e) { setPreviewError((e as Error).message); }
    finally { setPreviewing(null); }
  }, [plan, id, flush]);

  useEffect(() => {  // Ctrl+Enter previews the current shot
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); void runPreview(sel); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runPreview, sel]);

  // ---------- derived ----------
  const lines = perf?.lines ?? [];
  const hero = perf?.characters[HERO] ?? { voice_id: "" };
  const meModel = perf?.characters[HERO]?.model ?? AV_HERO;
  const buddyModel = perf?.characters[BUDDY]?.model ?? "buddy_claude";
  const buddy = cat?.buddies.find((b) => b.model === buddyModel);
  const buddyName = isPerson(buddyModel) ? personName(buddyModel) : buddy?.label ?? "Buddy";
  const meName = isPerson(meModel) ? personName(meModel) : "Me";
  const tintOf = (model: string) => (model === AV_HERO ? hero.outfit_color ?? PURPLE
    : isPerson(model) ? PERSON_ACCENT[model] : cat?.buddies.find((b) => b.model === model)?.shell ?? "#D97757");
  const color = (who: string) => tintOf(who === HERO ? meModel : buddyModel);
  const buddyIsBot = isBot(buddyModel);
  // what the look preview depends on: who is cast, how the low-poly hero is dressed, the room and the spot in it
  const lookKey = perf ? JSON.stringify([perf.characters, perf.environment, perf.room_view ?? null]) : "";
  const runtime = plan?.runtime ?? estimateRuntime(lines);
  const frames = Math.ceil(runtime * 30);
  const missing = lines.filter((l) => !["imported", "ready"].includes(voices[l.id]?.status ?? "missing")).length;
  const timing = cat?.timing;
  const est = timing && {
    preview: timing.preview_still_s,
    draft: timing.scene_load_s + frames * timing.draft_s_per_frame,
    balanced: timing.scene_load_s + frames * (timing.balanced_s_per_frame ?? timing.final_s_per_frame / 3),
    final: timing.scene_load_s + frames * timing.final_s_per_frame,
  };
  const running = live.job?.status === "running";
  const finals = data?.files.finals ?? [];
  const animaticDone = data?.files && live.job?.mode === "animatic" && live.job.status === "done";
  const overrides = perf?.camera?.overrides ?? {};
  const mix = plan?.split;
  const angleLabel = (a?: string) => cat?.angles?.find((x) => x.id === a)?.label;
  const [undoTake, setUndoTake] = useState<{ seed?: number; overrides: Record<string, unknown> } | null>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const [stripMore, setStripMore] = useState(false);
  const measureStrip = useCallback(() => {
    const el = stripRef.current;
    setStripMore(!!el && el.scrollWidth - el.scrollLeft - el.clientWidth > 4);
  }, []);
  useEffect(() => {
    measureStrip();
    window.addEventListener("resize", measureStrip);
    return () => window.removeEventListener("resize", measureStrip);
  }, [plan, measureStrip]);

  const runLook = useCallback(async () => {
    const token = ++lookSeq.current;
    setLookBusy(true);
    setLookError(null);
    try {
      await flush();
      const r = await api.avLook(id);
      if (token === lookSeq.current) { setLook(fileUrl(id, r.still, r.at)); setShowLook(true); }
    } catch (e) { if (token === lookSeq.current) setLookError((e as Error).message); }
    finally { if (token === lookSeq.current) setLookBusy(false); }
  }, [id, flush]);
  const lookReady = !!lines.length && !!cat?.allBuilt;
  useEffect(() => {
    if (!lookReady || !lookKey) return;
    setShowLook(true);
    const t = setTimeout(() => void runLook(), 1200);
    return () => clearTimeout(t);
  }, [lookKey, lookReady]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------- script edits ----------
  const setLines = (fn: (ls: PerfLine[]) => PerfLine[]) => update((p) => ({ ...p, lines: renumber(fn(p.lines)) }));
  const setLine = (i: number, patch: Partial<PerfLine>) => setLines((ls) => ls.map((l, k) => (k === i ? { ...l, ...patch } : l)));
  const addLine = (after: number) => {
    setLines((ls) => {
      const who = ls[after]?.speaker === HERO ? BUDDY : HERO;
      const next = [...ls];
      next.splice(after + 1, 0, makeLine(who, "", 0));
      return next;
    });
    focusLine.current = after + 1;
  };
  useEffect(() => {
    if (focusLine.current === null) return;
    document.querySelector<HTMLInputElement>(`[data-line="${focusLine.current}"]`)?.focus();
    focusLine.current = null;
  });
  const onLineKey = (e: RKeyboardEvent<HTMLInputElement>, i: number) => {
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey) { e.preventDefault(); addLine(i); }
    else if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); setLine(i, { speaker: lines[i].speaker === HERO ? BUDDY : HERO, action: "" }); }
    else if (e.key === "Escape") (e.target as HTMLInputElement).blur();
  };
  const pickCast = (slot: typeof HERO | typeof BUDDY, model: string) => update((p) => {
    const cur = p.characters[slot];
    const keepVoice = cur.voice_id && cur.voice_id !== defaultVoice(cur.model ?? (slot === HERO ? AV_HERO : "buddy_claude"));
    const next = { ...p, characters: { ...p.characters, [slot]: { ...cur, model, voice_id: keepVoice ? cur.voice_id : defaultVoice(model) } } };
    // a reaction clip belongs to a bot: drop them when the other speaker becomes a person
    return slot === BUDDY && !isBot(model) ? { ...next, lines: next.lines.map((l) => ({ ...l, action: "" })) } : next;
  });
  const setHero = (patch: Record<string, unknown>) => update((p) => ({ ...p, characters: { ...p.characters, [HERO]: { ...p.characters[HERO], ...patch } } }));
  const setCamera = (patch: Record<string, unknown>) => update((p) => ({ ...p, camera: { ...p.camera, ...patch } }));
  const setOverride = (shot: number, patch: Record<string, unknown> | null) => update((p) => {
    const ov = { ...(p.camera?.overrides ?? {}) };
    if (patch === null) delete ov[String(shot)]; else ov[String(shot)] = { ...ov[String(shot)], ...patch };
    return { ...p, camera: { ...p.camera, overrides: ov } };
  });
  const uploadMusic = async (f: File) => {
    const ext = (f.name.split(".").pop() ?? "mp3").toLowerCase();
    if (!["mp3", "wav", "m4a", "flac"].includes(ext)) return toast("Use an mp3, wav, m4a or flac file", "err");
    try { await api.upload(id, `media/music.${ext}`, f); toast("Music added: it mixes under the voices"); void load(); }
    catch (e) { toast((e as Error).message, "err"); }
  };

  // ---------- render ----------
  if (error) return <div className="page"><div className="page-inner"><Callout tone="err">Couldn't open this project: {error} <button className="btn btn-sm" onClick={() => void load()}><RefreshCw size={12} />Retry</button></Callout></div></div>;
  if (!perf || !data) return <div className="page"><div className="page-inner"><div className="skeleton" style={{ height: 480 }} /></div></div>;
  if (perf.style !== "shots-av") return <div className="page"><div className="page-inner"><Callout tone="info">This project isn't a Shots-AV reel. <Link to="/projects">Open it from Projects</Link>.</Callout></div></div>;

  const music = data.files.media.find((m) => /^music\.(mp3|wav|m4a|flac)$/i.test(m));
  const shotMenu = (i: number, rect: DOMRect) => {
    const s = plan!.shots[i];
    const ov = overrides[String(i)] ?? {};
    menu.openAt(rect, [
      { heading: `Shot ${i + 1} · angle` },
      ...(perf.camera?.angles === "classic" || perf.camera?.grammar === "reference"
        ? (Object.keys(SETUP_LABEL) as AvSetup[]).map((k) => ({ label: SETUP_LABEL[k], active: s.kind === k, onSelect: () => setOverride(i, { kind: k }) }))
        : (cat?.angles ?? []).filter((a) => a.role === roleOf(s.kind)).map((a) => ({ label: a.label, active: s.angle === a.id, onSelect: () => setOverride(i, { angle: a.id }) }))),
      ...(perf.camera?.angles === "classic" || perf.camera?.grammar === "reference" ? [] : [{ heading: "Switch to" },
        ...(["hero", "buddy", "wide"] as const).filter((r) => r !== roleOf(s.kind)).map((r) => ({
          label: r === "hero" ? "A shot of you" : r === "buddy" ? `A shot of ${buddyName}` : "A wide",
          onSelect: () => setOverride(i, { angle: (cat?.angles ?? []).find((a) => a.role === r)?.id }) }))]),
      { separator: true as const },
      { heading: "Move" },
      ...MOVES.map((m) => ({ label: MOVE_LABEL[m], active: s.move === m, onSelect: () => setOverride(i, { move: m }) })),
      { separator: true as const },
      { label: s.rack ? "Remove focus pull" : "Pull focus to the buddy", disabled: !s.kind.startsWith("av_wide"),
        onSelect: () => setOverride(i, { rack: !s.rack }) },
      { label: "Reset to the director's choice", disabled: !Object.keys(ov).length, onSelect: () => setOverride(i, null) },
    ]);
  };

  return (
    <div className="av-ws" data-tab={tab}>
      <h1 className="sr-only">{data.name}: desk reel</h1>
      <header className="av-head">
        <IconButton label="All desk reels" onClick={() => nav("/shots-av")}><ArrowLeft size={16} /></IconButton>
        <input className="input av-title" aria-label="Project name" defaultValue={data.name}
          onBlur={(e) => { const name = e.target.value.trim(); if (name && name !== data.name) void api.save(id, { editor: { ...data.editor, name } }).then(() => load()); }} />
        <span className="meta" aria-live="polite">{saved === "saving" ? "Saving…" : saved === "error" ? "Not saved" : "Saved"}</span>
        <div className="grow" />
        <div className="av-tabs" role="tablist" aria-label="Workspace panels">
          {(["script", "stage", "look"] as Tab[]).map((t) => (
            <button key={t} role="tab" className="tab" aria-selected={tab === t} onClick={() => setTab(t)}>{label(t)[0].toUpperCase() + t.slice(1)}</button>
          ))}
        </div>
      </header>

      {/* ---------------- Script ---------------- */}
      <section className="av-col av-script" aria-label="Script">
        <div className="av-col-head">
          <span className="h3 grow">Script</span>
          <button className="btn btn-sm" onClick={() => setPaste(true)}><ClipboardPaste size={13} />Paste script</button>
          <IconButton label="Add a line" size="sm" onClick={() => addLine(lines.length - 1)}><Plus size={14} /></IconButton>
        </div>
        <div className="av-lines">
          {!lines.length ? (
            <div className="av-empty">
              <Empty icon={<Wand2 size={18} />} title="Write your first line"
                action={<button className="btn btn-primary btn-sm" onClick={() => addLine(-1)}><Plus size={13} />Add a line</button>}>
                Or start from one of our scripts:
              </Empty>
              <div className="col" style={{ gap: 6 }}>
                {STARTERS.map((s) => (
                  <button key={s.id} className="btn" onClick={() => update((p) => ({ ...p, environment: s.room,
                    characters: { ...p.characters, [BUDDY]: { ...p.characters[BUDDY], model: s.buddy } },
                    lines: s.lines.map(([who, text, emo], i) => makeLine(who, text, i, emo)) }))}>{s.name}</button>
                ))}
              </div>
            </div>
          ) : lines.map((l, i) => {
            const v = voices[l.id]?.status ?? "missing";
            const isBuddy = l.speaker === BUDDY;
            return (
              <div key={l.id} className={`av-line ${isBuddy ? "buddy" : "me"}${plan?.shots[sel]?.line === l.id ? " current" : ""}`}>
                <div className="row" style={{ gap: 6 }}>
                  <Tooltip label="Switch speaker" kbd="Tab">
                    <button className="av-who" style={{ ["--who" as string]: color(l.speaker) }}
                      onClick={() => setLine(i, { speaker: isBuddy ? HERO : BUDDY, action: "" })} aria-label={`Speaker: ${isBuddy ? buddyName : meName}. Switch`}>
                      <span className="dot" />{isBuddy ? buddyName : meName}
                    </button>
                  </Tooltip>
                  <span className={`av-voice ${v}`} title={v === "imported" || v === "ready" ? "Voice ready" : "No voice yet"} />
                  <div className="grow" />
                  <IconButton label="Delete line" size="xs" onClick={() => setLines((ls) => ls.filter((_, k) => k !== i))}><Trash2 size={12} /></IconButton>
                </div>
                <input className="input av-text" data-line={i} value={l.text} placeholder={isBuddy ? `What ${buddyName} says` : meModel === AV_HERO ? "What you say" : `What ${meName} says`}
                  aria-label={`Line ${i + 1} text`} onChange={(e) => setLine(i, { text: e.target.value })} onKeyDown={(e) => onLineKey(e, i)} />
                <div className="row av-line-opts">
                  <Select size="sm" ariaLabel={`Line ${i + 1} emotion`} value={l.emotion}
                    options={EMOTIONS.map((e) => ({ value: e, label: e }))} onChange={(e) => setLine(i, { emotion: e as Emotion })} />
                  <button className="chip" aria-pressed={Boolean(l.beat)} onClick={() => setLine(i, { beat: !l.beat })}
                    title="Force a wide shot on this line">Beat</button>
                  {isBuddy && buddyIsBot && (
                    <Select size="sm" ariaLabel={`Line ${i + 1} buddy reaction`} value={l.action ?? ""}
                      options={["", ...(cat?.actions ?? [])].map((a) => ({ value: a, label: ACTION_LABEL[a] ?? a }))}
                      onChange={(a) => setLine(i, { action: a })} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <footer className="av-foot">
          <span><b>{lines.length}</b> lines · <b>{fmtSec(runtime)}</b></span>
          <span className="av-mix" title="Screen time: you / buddy / wides. The reference reel: 37 / 46 / 17">
            {(["hero", "buddy", "wide"] as const).map((g) => (
              <span key={g} className="av-mix-part">
                <span className="meta">{g === "hero" ? meName : g === "buddy" ? buddyName : "Wide"}</span>
                <b>{mix ? Math.round(mix[g] * 100) : "–"}%</b>
                <span className="meta">/{Math.round((cat?.target[g] ?? 0) * 100)}</span>
              </span>
            ))}
          </span>
          <span className="meta av-keys"><span className="kbd">Enter</span> new line · <span className="kbd">Tab</span> switch speaker · <span className="kbd">Esc</span> leave the line</span>
        </footer>
      </section>

      {/* ---------------- Stage ---------------- */}
      <section className="av-col av-stage" aria-label="Stage">
        <div className="av-actions">
          <button className="btn" disabled={!plan || previewing !== null} onClick={() => void runPreview(sel)}>
            <Eye size={14} />Preview shot{est && <>{" "}<span className="meta">{fmtDur(est.preview)}</span></>}<span className="kbd">Ctrl+↵</span>
          </button>
          <button className="btn" disabled={!lines.length || running} onClick={() => void start("animatic")} title="Silent, from estimated timing: no voices needed">
            <Film size={14} />Silent animatic{est && <>{" "}<span className="meta">{fmtDur(est.draft)}</span></>}
          </button>
          <span className="grow" />
          <Segmented size="sm" value={quality} onChange={setQuality}
            options={[{ value: "draft", label: `Draft${est ? ` ${mins(est.draft)}` : ""}`, title: "Half size, quick: for checking timing and angles" },
              { value: "balanced", label: `Balanced${est ? ` ${mins(est.balanced)}` : ""}`, title: "1080x1920, about 3x faster than Final; faces and colour match it by eye" },
              { value: "final", label: `Final${est ? ` ${mins(est.final)}` : ""}`, title: "1080x1920, every render setting at its highest" }]} />
          <button className="btn btn-primary" disabled={!lines.length || running || gen.phase === "voices" || gen.phase === "render"}
            onClick={() => void generateReel()} title="Make the voices with ElevenLabs, then the video on that audio">
            <Sparkles size={14} />Generate reel{est && <>{" "}<span className="meta">{fmtDur(est[quality])}</span></>}
          </button>
        </div>

        {catError ? <Callout tone="err">Couldn't read the Shots-AV assets: {catError} <button className="btn btn-sm" onClick={loadCatalog}>Retry</button></Callout>
         : cat && !cat.allBuilt && (
          <Callout tone="warn">
            <div className="col" style={{ gap: 8 }}>
              <span>The hero, buddies and rooms aren't built on this machine yet. It takes a few minutes, once.</span>
              {assets.job?.status === "running" ? (
                <pre className="av-log">{assets.log.slice(-6).join("\n") || "Starting Blender…"}</pre>
              ) : (
                <span><button className="btn btn-sm" onClick={() => void buildAssets()}><Hammer size={12} />Build Shots-AV assets</button>
                  {assets.job?.status === "failed" && <span className="err-text" style={{ marginLeft: 8 }}>The build failed; the log is below.</span>}</span>
              )}
              {assets.job?.status === "failed" && <pre className="av-log">{assets.log.slice(-20).join("\n")}</pre>}
            </div>
          </Callout>
        )}
        {gen.phase === "voices" && (
          <div className="av-job panel" aria-live="polite">
            <div className="row"><Spinner /><span className="grow">Making voices with ElevenLabs: {gen.done} of {gen.total} lines</span></div>
            <div className="av-progress"><span style={{ width: `${((gen.done ?? 0) / (gen.total || 1)) * 100}%` }} /></div>
            <span className="meta">Each line is performed with its emotion. The video starts as soon as every line has a take.</span>
          </div>
        )}
        {gen.phase === "error" && (
          <Callout tone="err">
            <div className="col" style={{ gap: 6 }}>
              <span>Couldn't make the voices.</span>
              <pre className="av-log">{gen.error}</pre>
              <span className="row">{!sys?.elevenlabsKey && <Link className="btn btn-sm" to="/settings"><SettingsIcon size={12} />Open Settings</Link>}
                <button className="btn btn-sm" onClick={() => setGen({ phase: "idle" })}>Dismiss</button></span>
            </div>
          </Callout>
        )}
        {lines.length > 0 && missing > 0 && gen.phase === "idle" && (
          <Callout tone="info">
            {missing} of {lines.length} lines have no voice yet. <b>Generate reel</b> makes them with ElevenLabs
            {sys && !sys.elevenlabsKey ? <> (add your key in <Link to="/settings">Settings</Link> first)</> : " using your key from Settings"}, performing each
            line's emotion, then renders the video on that audio. You can also drop your own <span className="mono">l01.mp3</span>… into{" "}
            <span className="mono">out/audio</span> or use the <Link to="/voices" onClick={() => void useProject.getState().load(id)}>Voices page</Link>.
          </Callout>
        )}

        {live.job && (
          <div className="av-job panel" aria-live="polite">
            {live.job.status === "running" ? (
              <>
                <div className="row"><Spinner /><span className="grow">{live.job.mode === "animatic" ? "Silent animatic" : live.job.draft ? "Draft reel" : "Full-size render"}: frame {live.frame || "…"} of {frames}</span>
                  <button className="btn btn-sm" onClick={() => void api.cancel(live.job!.id).then(() => toast("Cancelled"))}><X size={12} />Cancel</button></div>
                <div className="av-progress"><span style={{ width: `${Math.min(100, (live.frame / frames) * 100)}%` }} /></div>
                <pre className="av-log">{live.log.slice(-4).join("\n")}</pre>
              </>
            ) : live.job.status === "failed" ? (
              <>
                <div className="row"><Badge tone="err">Failed</Badge><span className="grow meta">The last lines of the log:</span>
                  <IconButton label="Dismiss" size="xs" onClick={() => setLive({ job: null, log: [], frame: 0 })}><X size={12} /></IconButton></div>
                <pre className="av-log">{(live.job.error ?? live.log.slice(-20).join("\n")).split("\n").slice(-20).join("\n")}</pre>
              </>
            ) : live.job.status === "done" ? (
              <div className="row"><Badge tone="ok">Done</Badge>
                <span className="mono meta grow ellipsis">{data.folder}/out/{live.job.mode === "animatic" ? "animatic.mp4" : finals[0]}</span>
                <button className="btn btn-sm" onClick={() => void api.reveal(id).catch((e) => toast((e as Error).message, "err"))}><FolderOpen size={12} />Open folder</button></div>
            ) : <div className="row"><Badge>Cancelled</Badge></div>}
          </div>
        )}

        <div className="av-frame-wrap">
          <div className="av-frame">
            {live.job && (live.job.status !== "running") && live.job.status === "done" && (finals.length || animaticDone) ? (
              <video key={live.job.id} controls src={fileUrl(id, live.job.mode === "animatic" ? "out/animatic.mp4" : `out/${finals[0]}`, live.job.endedAt)} />
            ) : preview && preview.shot === sel && !showLook ? (
              <img src={preview.url} alt={`Preview of shot ${sel + 1}`} />
            ) : look && previewing === null ? (
              <img src={look} alt={`Look preview: ${meName} at the desk${perf.environment ? "" : ""}`} />
            ) : (
              <div className="av-frame-empty">
                {previewing !== null ? <><Spinner /><span className="meta">Rendering shot {previewing + 1}…</span></>
                  : lookBusy ? <><Spinner /><span className="meta">Dressing the set…</span></>
                  : <><Camera size={20} /><span className="meta">{lines.length ? "Change the cast or the outfit to see them here, or pick a shot below" : "Write a few lines to see the shots"}</span></>}
              </div>
            )}
            {(showLook || !(preview && preview.shot === sel)) && look && previewing === null && (
              <span className="av-frame-tag">{lookBusy ? <><Spinner />Updating the look…</> : "Look preview"}</span>
            )}
            {((previewing !== null && preview) || (lookBusy && look && showLook)) && <div className="av-frame-busy"><Spinner /></div>}
          </div>
          {previewError && <Callout tone="err">The preview failed: <pre className="av-log">{previewError}</pre></Callout>}
          {lookError && <Callout tone="err">The look preview failed: <pre className="av-log">{lookError.split("\n").slice(-6).join("\n")}</pre></Callout>}
        </div>

        <div className="av-strip-head row">
          <span className="label grow">Shots</span>
          {planError ? <span className="err-text meta">Couldn't plan the shots</span> : plan && <span className="meta">{plan.shots.length} shots · cut on every line</span>}
        </div>
        <div ref={stripRef} className={`av-strip${stripMore ? " more" : ""}`} role="listbox" aria-label="Shots" onScroll={measureStrip}>
          {plan?.shots.map((s) => (
            <div key={s.index} role="option" aria-selected={s.index === sel} tabIndex={0}
              className={`av-tile${s.index === sel ? " sel" : ""}${overrides[String(s.index)] ? " edited" : ""}`}
              style={{ flexGrow: Math.max(1, s.end - s.start), ["--who" as string]: color(s.speaker === "hero" ? HERO : BUDDY) }}
              onClick={() => void runPreview(s.index)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); void runPreview(s.index); } }}
              title={`${angleLabel(s.angle) ?? SETUP_LABEL[s.kind]} · ${MOVE_LABEL[s.move] ?? s.move}${s.rack ? " · focus pull" : ""}`}>
              <span className="av-tile-setup">{ROLE_SHORT[roleOf(s.kind)]}</span>
              <span className="av-tile-len mono">{(s.end - s.start).toFixed(1)}s</span>
              {s.angle && <span className="av-angle-tag">{angleLabel(s.angle) ?? SETUP_LABEL[s.kind]}</span>}
              {previewing === s.index && <Spinner />}
              <button className="av-tile-menu" aria-label={`Shot ${s.index + 1} options`}
                onClick={(e) => { e.stopPropagation(); shotMenu(s.index, e.currentTarget.getBoundingClientRect()); }}><MoreHorizontal size={12} /></button>
            </div>
          ))}
        </div>
        {plan && <div className="meta av-legend">Each shot shows who is on screen, the angle and its length. The director picks angles from each line's mood; a shot's ⋯ menu picks your own.</div>}
      </section>

      {/* ---------------- Look ---------------- */}
      <section className="av-col av-look" aria-label="Look">
        {!cat ? <div className="skeleton" style={{ height: 320, margin: 12 }} /> : <>
          <Section title="Cast">
            <div className="eyebrow" style={{ margin: "2px 0 6px" }}>At the desk</div>
            <div className="av-cards four" role="radiogroup" aria-label="Who sits at the desk">
              {[AV_HERO, ...PEOPLE].map((m) => (
                <button key={m} className="av-card" role="radio" aria-checked={meModel === m} aria-pressed={meModel === m}
                  disabled={m !== AV_HERO && (cat.built.people?.[m] !== false ? m === buddyModel : true)}
                  title={m === AV_HERO ? "Your low-poly hero" : m === buddyModel ? `${personName(m)} is already talking to you` : `${personName(m)}, realistic, seated at the desk`}
                  onClick={() => pickCast(HERO, m)}>
                  <AvThumb id={m === AV_HERO ? `outfit_${hero.outfit ?? "puffer"}` : `person_${m}`} alt="" />
                  <span className="av-card-name"><span className="dot" style={{ background: tintOf(m) }} />{m === AV_HERO ? "You (AV)" : personName(m)}</span>
                </button>
              ))}
            </div>
            <div className="eyebrow" style={{ margin: "12px 0 6px" }}>Talking to</div>
            <div className="av-cards four" role="radiogroup" aria-label="Who you talk to">
              {[...cat.buddies.map((b) => b.model), ...PEOPLE].map((m) => (
                <button key={m} className="av-card" role="radio" aria-checked={buddyModel === m} aria-pressed={buddyModel === m}
                  disabled={isPerson(m) && (cat.built.people?.[m] !== false ? m === meModel : true)}
                  title={isPerson(m) ? (m === meModel ? `${personName(m)} is at the desk` : `${personName(m)}, in the guest chair`) : cat.buddies.find((b) => b.model === m)?.readsAs}
                  onClick={() => pickCast(BUDDY, m)}>
                  <AvThumb id={isPerson(m) ? `person_${m}` : m} alt="" />
                  <span className="av-card-name"><span className="dot" style={{ background: tintOf(m) }} />{isPerson(m) ? personName(m) : cat.buddies.find((b) => b.model === m)?.label}</span>
                </button>
              ))}
            </div>
            {meModel !== AV_HERO && <div className="meta" style={{ marginTop: 8 }}>{meName} is a realistic model in their own outfit. Pick You (AV) to dress your low-poly hero.</div>}
          </Section>
          {meModel === AV_HERO && <Section title="Your look">
            <div className="eyebrow" style={{ margin: "2px 0 6px" }}>Outfit</div>
            <div className="av-cards three av-outfits" role="radiogroup" aria-label="Outfit">
              {(cat.hero.outfit.options ?? []).map((o) => (
                <button key={o} className="av-card" role="radio" aria-checked={(hero.outfit ?? "puffer") === o}
                  aria-pressed={(hero.outfit ?? "puffer") === o} title={cat.outfits[o] ?? label(o)}
                  onClick={() => setHero({ outfit: o, outfit_color: cat.outfitColors?.[o] ?? PURPLE })}>
                  <AvThumb id={`outfit_${o}`} alt="" />
                  <span className="av-card-name"><span className="dot" style={{ background: cat.outfitColors?.[o] ?? PURPLE }} />{cat.outfits[o] ?? label(o)}</span>
                </button>
              ))}
            </div>
            <FieldRow label="Jacket">
              <div className="av-swatches">
                {(cat.hero.outfit_color.swatches ?? []).map((c) => (
                  <button key={c} className="swatch av-swatch" aria-pressed={(hero.outfit_color ?? PURPLE).toUpperCase() === c.toUpperCase()}
                    aria-label={`Jacket colour ${c}`} style={{ background: c }} onClick={() => setHero({ outfit_color: c })} />
                ))}
                <ColorInput label="Custom jacket colour" value={hero.outfit_color ?? PURPLE} onChange={(c) => setHero({ outfit_color: c })} />
              </div>
            </FieldRow>
            <FieldRow label="Hair"><Select size="sm" ariaLabel="Hair" value={hero.hair ?? String(cat.hero.hair.default)}
              options={(cat.hero.hair.options ?? []).map((o) => ({ value: o, label: label(o) }))} onChange={(v) => setHero({ hair: v })} /></FieldRow>
            <FieldRow label="Glasses"><Select size="sm" ariaLabel="Glasses" value={hero.glasses ?? String(cat.hero.glasses.default)}
              options={(cat.hero.glasses.options ?? []).map((o) => ({ value: o, label: label(o) }))} onChange={(v) => setHero({ glasses: v })} /></FieldRow>
            <FieldRow label="Headphones"><Select size="sm" ariaLabel="Headphones" value={hero.headphones ?? String(cat.hero.headphones.default)}
              options={(cat.hero.headphones.options ?? []).map((o) => ({ value: o, label: label(o) }))} onChange={(v) => setHero({ headphones: v })} /></FieldRow>
            <FieldRow label="Skin">
              <div className="av-swatches">
                {Object.entries(cat.skins).map(([k, c]) => (
                  <Tooltip key={k} label={label(k)}>
                    <button className="swatch av-swatch round" aria-label={`Skin ${label(k)}`} style={{ background: c }}
                      aria-pressed={(hero.skin ?? String(cat.hero.skin.default)) === k} onClick={() => setHero({ skin: k })} />
                  </Tooltip>
                ))}
              </div>
            </FieldRow>
            <FieldRow label="Beard"><Select size="sm" ariaLabel="Beard" value={hero.beard ?? String(cat.hero.beard?.default ?? "light")}
              options={(cat.hero.beard?.options ?? []).map((o) => ({ value: o, label: label(o) }))} onChange={(v) => setHero({ beard: v })} /></FieldRow>
            <FieldRow label="Stubble"><Slider ariaLabel="Stubble" value={hero.stubble ?? 0.3} onChange={(v) => setHero({ stubble: Math.round(v * 100) / 100 })} /></FieldRow>
          </Section>}
          <Section title="Room">
            {([["gamer", "Gamer and editor rooms"], ["dark", "Dark"], ["light", "Light"], ["classic", "Classic sets"]] as const).map(([group, name]) => (
              <div key={group}>
                <div className="eyebrow" style={{ margin: "4px 0 6px" }}>{name}</div>
                <div className="av-cards three">
                  {cat.rooms.filter((r) => (group === "gamer" ? r.gamer : group === "classic" ? r.classic : !r.gamer && !r.classic && r.tone === group)).map((r) => (
                    <button key={r.id} className="av-card tall" aria-pressed={perf.environment === r.id} title={r.look}
                      onClick={() => update((p) => ({ ...p, environment: r.id, room_view: undefined }))}>
                      <AvThumb id={r.id} alt="" />
                      <span className="av-card-name">{r.label}</span>
                    </button>
                  ))}
                </div>
                {(() => {  // your spot in the room, right under the room you picked
                  const room = cat.rooms.find((r) => r.id === perf.environment);
                  const inGroup = group === "gamer" ? room?.gamer : group === "classic" ? room?.classic : room && !room.gamer && !room.classic && room.tone === group;
                  if (!room || !inGroup) return null;
                  return (
                    <div className="av-spot">
                      <div className="eyebrow" style={{ margin: "10px 0 6px" }}>Your spot in {room.label}</div>
                      <RoomFramePicker roomId={room.id} label={room.label} pano={room.pano} view={perf.room_view} spots={room.spots ?? []}
                        onChange={(v) => update((p) => ({ ...p, room_view: v ?? undefined }))} />
                    </div>
                  );
                })()}
              </div>
            ))}
          </Section>
          <Section title="Camera">
            <FieldRow label="Angles"><Segmented size="sm" full value={perf.camera?.angles ?? "varied"} onChange={(v) => setCamera({ angles: v })}
              options={[{ value: "varied", label: `Director · ${cat.angles?.length ?? 36} angles`, title: "The director picks from 36 angles by each line's mood: low, high, profile, dutch, over the shoulder, inserts" },
                { value: "classic", label: "Classic 5", title: "The reference reel's five set-ups" }]} /></FieldRow>
            {(perf.camera?.angles ?? "varied") === "varied" && (
              <FieldRow label="Take"><span className="row" style={{ gap: 8 }}>
                <button className="btn btn-sm" onClick={() => {
                  setUndoTake({ seed: perf.camera?.seed, overrides: perf.camera?.overrides ?? {} });
                  setCamera({ seed: Math.floor(Math.random() * 1e6), overrides: {} });
                }} title="Shoot the reel again with a different set of angles"><Dices size={12} />Reroll angles</button>
                {undoTake && <button className="btn btn-sm btn-ghost" onClick={() => { setCamera(undoTake); setUndoTake(null); }}
                  title="Back to the previous angles and your per-shot picks">Undo</button>}
              </span></FieldRow>
            )}
            {(perf.camera?.angles ?? "varied") === "varied" && Object.keys(overrides).length > 0 && (
              <div className="meta">Rerolling also clears your {Object.keys(overrides).length} per-shot {Object.keys(overrides).length === 1 ? "pick" : "picks"}; Undo brings them back.</div>
            )}
            <FieldRow label="Grammar"><Segmented size="sm" full value={perf.camera?.grammar ?? "signature"} onChange={(v) => setCamera({ grammar: v })}
              options={[{ value: "signature", label: "Signature", title: "The reference's cutting, plus a gentle ease, a little sway and a focus pull" },
                { value: "reference", label: "Reference", title: "The reference reel's rules, exactly" }]} /></FieldRow>
            <FieldRow label="Drift"><Slider ariaLabel="Camera drift" min={0} max={2} step={0.1} value={perf.camera?.drift ?? 1}
              format={(v) => `${v.toFixed(1)}×`} onChange={(v) => setCamera({ drift: Math.round(v * 10) / 10 })} /></FieldRow>
            <FieldRow label="Focus pull"><Switch label="Focus pull in the first wide" checked={perf.camera?.rack !== false} onChange={(v) => setCamera({ rack: v })} /></FieldRow>
            <FieldRow label="Connected move"><Switch label="One shot arcs from you to the buddy instead of cutting" checked={perf.camera?.connect !== false}
              onChange={(v) => setCamera({ connect: v })} /></FieldRow>
          </Section>
          <Section title="Voices">
            <FieldRow label={meModel === AV_HERO ? "You" : meName}><Select size="sm" ariaLabel={`${meName}'s voice`} value={perf.characters[HERO]?.voice_id || defaultVoice(meModel)}
              options={VOICES.map((v) => ({ value: v.id, label: `${v.name} · ${v.tags.slice(0, 2).join(", ")}` }))}
              onChange={(v) => setHero({ voice_id: v })} /></FieldRow>
            <FieldRow label={buddyName}><Select size="sm" ariaLabel={`${buddyName}'s voice`} value={perf.characters[BUDDY]?.voice_id || defaultVoice(buddyModel)}
              options={VOICES.map((v) => ({ value: v.id, label: `${v.name} · ${v.tags.slice(0, 2).join(", ")}` }))}
              onChange={(v) => update((p) => ({ ...p, characters: { ...p.characters, [BUDDY]: { ...p.characters[BUDDY], voice_id: v } } }))} /></FieldRow>
            <div className="meta">ElevenLabs performs each line's emotion (happy, worried, deadpan…) with audio tags; intense lines get its most expressive setting. Voices sit in the room with a touch of its acoustics.</div>
          </Section>
          <Section title="Captions">
            <CaptionsPanel style={perf.captions?.style ?? SHOTSAV_TOP_STYLE} captions={perf.captions ?? {}} onOpen={() => setSubsOpen(true)}
              still={preview?.url} sample={lines.find((l) => l.text.trim())?.text ?? "The client signed off."}
              endText={perf.end_text ?? ""} onEndText={(v) => update((p) => ({ ...p, end_text: v }))}
              onStyle={(patch) => update((p) => ({ ...p, captions: { ...p.captions, style: { ...(p.captions?.style ?? SHOTSAV_TOP_STYLE), ...patch } } }))}
              onCaptions={(patch) => update((p) => ({ ...p, captions: { ...p.captions, ...patch } }))} />
          </Section>
          <Section title="Sound">
            <FieldRow label="Room tone"><Switch label="Room tone" checked={perf.ambience !== false} onChange={(v) => update((p) => ({ ...p, ambience: v }))} /></FieldRow>
            <FieldRow label="Foley"><Switch label="Keyboard taps and buddy chime" checked={perf.sound?.foley !== false} onChange={(v) => update((p) => ({ ...p, sound: { ...p.sound, foley: v } }))} /></FieldRow>
            <FieldRow label="Music">
              <label className="btn btn-sm av-file">
                {music ? <><Music size={12} /><span className="ellipsis">{music}</span></> : <><AudioLines size={12} />Add your music</>}
                <input type="file" accept=".mp3,.wav,.m4a,.flac,audio/*" onChange={(e) => { const f = e.target.files?.[0]; if (f) void uploadMusic(f); e.target.value = ""; }} />
              </label>
            </FieldRow>
          </Section>
        </>}
      </section>

      {subsOpen && (
        <Dialog title="Choose a template" wide icon={<CaptionsIcon size={16} />} onClose={() => setSubsOpen(false)}
          footer={<button className="btn btn-primary" onClick={() => setSubsOpen(false)}>Done</button>}>
          <div className="col" style={{ gap: 10 }}>
            <div className="grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
              <SubtitleCard s={SHOTSAV_TOP_STYLE} name="Shots-AV Top" note="This style's default"
                selected={(perf.captions?.style?.templateId ?? SHOTSAV_TOP_ID) === SHOTSAV_TOP_ID}
                onClick={() => update((p) => ({ ...p, captions: { ...p.captions, style: { ...SHOTSAV_TOP_STYLE } } }))} />
            </div>
            <SubtitleGrid value={perf.captions?.style?.templateId ?? SHOTSAV_TOP_ID}
              onPick={(st) => update((p) => ({ ...p, captions: { ...p.captions, style: st } }))} />
          </div>
        </Dialog>
      )}
      {paste && <PasteDialog buddyName={buddyName} hasLines={lines.length > 0} onClose={() => setPaste(false)}
        onUse={(ls) => { update((p) => ({ ...p, lines: ls })); setPaste(false); toast(`${ls.length} lines added`); }} />}
      {menu.node}
    </div>
  );
}

function PasteDialog({ buddyName, hasLines, onClose, onUse }: { buddyName: string; hasLines: boolean; onClose: () => void; onUse: (ls: PerfLine[]) => void }) {
  const [text, setText] = useState("");
  const parsed = useMemo(() => parseScript(text), [text]);
  return (
    <Dialog title="Paste a script" onClose={onClose} icon={<ClipboardPaste size={16} />}
      footer={<><span className="meta grow">{parsed.length} lines{hasLines ? " · replaces the current script" : ""}</span>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!parsed.length} onClick={() => onUse(parsed)}>Use script</button></>}>
      <textarea className="textarea" rows={10} autoFocus value={text} onChange={(e) => setText(e.target.value)}
        placeholder={`Me: The client signed off.\n${buddyName}: That's great!\nMe: Six rounds of feedback, though.`} />
      <div className="hint">One line per row. <span className="mono">Me:</span> or <span className="mono">You:</span> is you; any other name is {buddyName}. Rows without a name take turns.</div>
      {parsed.length > 0 && (
        <div className="av-paste-preview">
          {parsed.slice(0, 6).map((l) => <span key={l.id} className={`av-bubble ${l.speaker === HERO ? "me" : "buddy"}`}>{l.text}</span>)}
          {parsed.length > 6 && <span className="meta">and {parsed.length - 6} more</span>}
        </div>
      )}
    </Dialog>
  );
}

function CaptionsPanel({ style, captions, onOpen, onStyle, onCaptions, still, sample, endText, onEndText }: {
  style: SubtitleStyle; captions: NonNullable<Performance["captions"]>; onOpen: () => void;
  onStyle: (patch: Partial<SubtitleStyle>) => void; onCaptions: (patch: Record<string, unknown>) => void;
  still?: string; sample: string; endText: string; onEndText: (v: string) => void;
}) {
  const custom = captions.position === "custom";
  const top = style.templateId === SHOTSAV_TOP_ID;
  const plate = parseRgba(style.background);
  return (
    <div className="col" style={{ gap: 10 }}>
      <div className="av-sub-current">
        <SubtitleCard s={top ? { ...style, size: 52 } : style} name={top ? "Shots-AV Top" : SUBTITLE_TEMPLATES.find((t) => t.id === style.templateId)?.name ?? "Custom"} selected={false} onClick={onOpen} />
        <button className="btn btn-sm" onClick={onOpen}><CaptionsIcon size={12} />Change template</button>
      </div>
      {top ? (
        <>
          <FieldRow label="Text"><ColorInput label="Caption text colour" value={style.color} onChange={(v) => onStyle({ color: v })} /></FieldRow>
          <FieldRow label="Plate"><Switch label="Plate behind captions" checked={captions.plate !== false} onChange={(v) => onCaptions({ plate: v })} /></FieldRow>
          {captions.plate !== false && <>
            <FieldRow label="Plate colour"><ColorInput label="Plate colour" value={plate.hex} onChange={(v) => onStyle({ background: toRgba(v, plate.a) })} /></FieldRow>
            <FieldRow label="Plate opacity"><Slider ariaLabel="Plate opacity" value={plate.a} min={0.1} max={1} step={0.05}
              format={(v) => `${Math.round(v * 100)}%`} onChange={(v) => onStyle({ background: toRgba(plate.hex, v) })} /></FieldRow>
          </>}
          {!custom && <FieldRow label="Position"><Segmented size="sm" full value={captions.position ?? "top"} onChange={(v) => onCaptions({ position: v })}
            options={[{ value: "top", label: "Top" }, { value: "lower", label: "Lower" }]} /></FieldRow>}
          <FieldRow label="Speaker dot"><Switch label="Speaker colour dot" checked={captions.tint !== false} onChange={(v) => onCaptions({ tint: v })} /></FieldRow>
        </>
      ) : <SubtitleControls s={style} onChange={onStyle} />}
      <FieldRow label="Size"><Slider ariaLabel="Caption size" min={0.5} max={2} step={0.05} value={captions.size ?? 1}
        format={(v) => `${Math.round(v * 100)}%`} onChange={(v) => onCaptions({ size: Math.round(v * 100) / 100 })} /></FieldRow>
      <FieldRow label="Place by hand"><Switch label="Place the captions by hand" checked={custom}
        onChange={(v) => onCaptions(v ? { position: "custom", x: captions.x ?? 0.5, y: captions.y ?? (top ? 0.12 : 0.79) } : { position: top ? "top" : "lower" })} /></FieldRow>
      {custom && <>
        <CaptionPlacer x={captions.x ?? 0.5} y={captions.y ?? 0.12} size={captions.size ?? 1} still={still} sample={sample}
          onChange={(p) => onCaptions(p)} />
        <div className="meta">Drag the caption, or use the arrow keys. The striped bands are where platform buttons sit{still ? "" : "; preview a shot to see it behind"}.</div>
      </>}
      <FieldRow label="End card"><input className="input input-sm" aria-label="End card text" maxLength={120} placeholder="A closing line over the last wide"
        onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }}
        defaultValue={endText} onBlur={(e) => { if (e.target.value.trim() !== endText) onEndText(e.target.value.trim()); }} /></FieldRow>
    </div>
  );
}
