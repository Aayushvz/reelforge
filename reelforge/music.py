"""Background music for Shots-AV reels: the track library, script-based auto-pick, and the ducked music bed.

Library (assets/music/):
  catalog.json   the built-in pack (committed; the mp3s in tracks/ are git-ignored, `reelforge music fetch` gets them)
  mine/          the owner's own tracks and mine/catalog.json (git-ignored); vocals allowed
  trending.json  viral sounds as named slots; once the owner attaches a file, that track is a "mine" entry with viral=true

Auto-pick reads the script (emotion, intensity, mood, punchlines, a few words) into a genre profile and scores every
track against it. The bed starts at the track's hook, loops with a crossfade, and dips under every spoken line.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import hashlib
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "assets" / "music"
GENRES = ("comedy", "quirky", "suspense", "wholesome", "hype", "lofi", "sad", "romantic", "reveal", "drama")
GENRE_ENERGY = {"comedy": 0.55, "quirky": 0.5, "suspense": 0.5, "wholesome": 0.5, "hype": 0.9, "lofi": 0.25,
                "sad": 0.2, "romantic": 0.3, "reveal": 0.7, "drama": 0.55}

# what each emotion / mood asks of the music (genre weights)
EMOTION_GENRES = {
    "neutral": {}, "happy": {"wholesome": 1.0, "hype": 0.3}, "sad": {"sad": 1.0, "drama": 0.4},
    "worried": {"suspense": 0.7, "drama": 0.3}, "surprised": {"reveal": 0.5, "comedy": 0.3, "hype": 0.2},
    "smug": {"comedy": 0.7, "quirky": 0.3}, "deadpan": {"comedy": 1.0, "quirky": 0.2},
    "confused": {"quirky": 0.8, "comedy": 0.3}, "annoyed": {"comedy": 0.5, "drama": 0.3},
    "thinking": {"lofi": 0.6, "quirky": 0.2}, "embarrassed": {"comedy": 0.6, "quirky": 0.4},
}
MOOD_GENRES = {
    "calm": {"lofi": 0.6, "wholesome": 0.3}, "success": {"hype": 0.7, "reveal": 0.5, "wholesome": 0.3},
    "panic": {"suspense": 0.8, "hype": 0.3, "comedy": 0.2}, "awkward": {"comedy": 0.7, "quirky": 0.6},
    "reveal": {"reveal": 0.8, "suspense": 0.3}, "sad": {"sad": 0.9, "drama": 0.4, "romantic": 0.2},
}
WORD_GENRES = [
    (re.compile(r"\b(love|crush|date|kiss|heart|miss you|girlfriend|boyfriend)\b", re.I), {"romantic": 1.0}),
    (re.compile(r"\b(lol|haha|bro|bruh|wait what|seriously|literally)\b", re.I), {"comedy": 0.6}),
    (re.compile(r"\b(won|launch|shipped|finally|let'?s go|signed|promoted|viral)\b", re.I), {"hype": 0.6, "reveal": 0.3}),
    (re.compile(r"\b(fired|deadline|crash|panic|lost)\b", re.I), {"suspense": 0.6}),
    # the you-vs-your-AI banter: exasperation reads as comedy, not tension
    (re.compile(r"\b(why|still|again|exact|times|really|actually|bug|fix(ed)?|broken)\b|\?!|!\?", re.I),
     {"comedy": 0.5, "quirky": 0.2}),
]
# a two-hander at a desk is banter first: a light lean to comedy that real emotion in the script outweighs
BANTER_PRIOR = {"comedy": 0.25, "quirky": 0.15}

BASE_LUFS = -22.0          # the bed in the pauses (instrumental)
VOCAL_BASE_LUFS = -26.0    # songs sit lower: their lyrics compete with the voices
DUCK_DB = -9.0             # under speech (instrumental)
VOCAL_DUCK_DB = -14.0      # under speech (song with vocals)
END_LIFT_DB = 2.0          # once the last line is said
XFADE = 1.5                # loop crossfade (s)


@dataclass
class Track:
    id: str
    title: str
    artist: str = ""
    source: str = "mixkit"     # mixkit | mine
    file: str = ""             # path relative to assets/music
    duration: float = 0.0
    start: float = 0.0         # the hook: where the bed begins
    vocals: bool = False
    viral: bool = False
    energy: float = 0.5
    moods: dict = field(default_factory=dict)   # genre -> weight
    url: str = ""
    licence: str = ""
    sha256: str = ""
    note: str = ""

    @property
    def path(self) -> Path:
        return LIB / self.file


# ---------- library ----------
def _read(path: Path) -> list[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def validate(entries: list[dict]) -> list[str]:
    errors, seen = [], set()
    for i, e in enumerate(entries):
        where = e.get("id", f"#{i}")
        for k in ("id", "title", "file"):
            if not isinstance(e.get(k), str) or not e.get(k):
                errors.append(f"{where}: {k} is required")
        if e.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(e.get("id"))
        moods = e.get("moods") or {}
        if not isinstance(moods, dict) or not moods:
            errors.append(f"{where}: moods must name at least one genre")
        for g, w in (moods.items() if isinstance(moods, dict) else []):
            if g not in GENRES:
                errors.append(f"{where}: unknown genre {g!r} (one of {GENRES})")
            elif not isinstance(w, (int, float)) or w < 0:
                errors.append(f"{where}: genre weight must be a number >= 0")
        if not 0.0 <= float(e.get("energy", 0.5)) <= 1.0:
            errors.append(f"{where}: energy must be 0..1")
        if e.get("source") == "mixkit" and e.get("licence") != "Mixkit Stock Music Free License":
            errors.append(f"{where}: built-in tracks must be no-credit (Mixkit Stock Music Free License)")
    return errors


def _track(e: dict) -> Track:
    keys = Track.__dataclass_fields__
    return Track(**{k: v for k, v in e.items() if k in keys})


def library(include_missing: bool = False, lib: Path | None = None) -> list[Track]:
    """Built-in pack + the owner's tracks (owner tracks first). Tracks whose file isn't on disk are skipped."""
    lib = lib or LIB
    out = []
    for e in _read(lib / "mine" / "catalog.json") + _read(lib / "catalog.json"):
        t = _track(e)
        if include_missing or (lib / t.file).exists():
            out.append(t)
    return out


def trending(lib: Path | None = None) -> list[dict]:
    lib = lib or LIB
    mine = {e["id"]: e for e in _read(lib / "mine" / "catalog.json")}
    rows = []
    for slot in _read(lib / "trending.json"):
        rows.append({**slot, "added": slot["id"] in mine and (lib / mine[slot["id"]]["file"]).exists()})
    return rows


def find(track_id: str, lib: Path | None = None) -> Track | None:
    return next((t for t in library(lib=lib) if t.id == track_id), None)


# ---------- analysis (ffmpeg only) ----------
def loudness_curve(path: Path) -> tuple[list[float], float]:
    """Short-term loudness (LUFS) once a second, and the integrated loudness."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-filter_complex",
                        "ebur128=framelog=info", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    curve, integrated = {}, -70.0
    for line in r.stderr.splitlines():
        m = re.search(r"t:\s*([\d.]+).*?S:\s*(-?[\d.]+).*?I:\s*(-?[\d.]+)", line)
        if m:
            sec = int(float(m.group(1)))
            curve[sec] = float(m.group(2))
            integrated = float(m.group(3))
    return [curve[k] for k in sorted(curve)], integrated


def find_hook(curve: list[float], integrated: float, vocals: bool, window: int = 20) -> float:
    """Songs: the loudest sustained `window` seconds (the chorus, usually). Instrumentals: the first second that
    isn't a quiet intro. Always leaves at least 15 s to play."""
    n = len(curve)
    if n <= 16:
        return 0.0
    last = max(0, n - 15)
    if vocals:
        best, at = -1e9, 0
        for s in range(0, last + 1):
            seg = curve[s:s + window]
            v = sum(seg) / len(seg)
            if v > best + 0.75:  # a later window must be clearly louder to win
                best, at = v, s
        return float(at)
    for s, v in enumerate(curve[:last + 1]):
        if v > integrated - 8.0:  # S is a 3 s window ending at s: the music started about 3 s earlier
            return float(max(0, s - 3))
    return 0.0


def analyze(path: Path, vocals: bool) -> dict:
    curve, integrated = loudness_curve(path)
    dur = float(len(curve))
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True)
        dur = float(r.stdout.strip())
    except ValueError:
        pass
    return {"duration": round(dur, 2), "start": find_hook(curve, integrated, vocals), "loudness": round(integrated, 1)}


# ---------- auto-pick ----------
def profile(lines) -> dict:
    """Genre profile + target energy of a script. `lines` are schema Lines (or dicts with the same keys)."""
    g = dict.fromkeys(GENRES, 0.0)
    energy, total_w = 0.0, 0.0
    get = (lambda l, k, d=None: l.get(k, d)) if lines and isinstance(lines[0], dict) else \
        (lambda l, k, d=None: getattr(l, k, d))
    for l in lines:
        inten = float(get(l, "intensity", 0.5))
        w = 0.5 + inten
        for src in (EMOTION_GENRES.get(get(l, "emotion", "neutral"), {}), MOOD_GENRES.get(get(l, "mood", "calm"), {})):
            for k, v in src.items():
                g[k] += w * v
        if get(l, "punchline", False):
            g["comedy"] += 1.0
        for rx, add in WORD_GENRES:
            if rx.search(str(get(l, "text", ""))):
                for k, v in add.items():
                    g[k] += v
        lift = {"panic": 0.2, "success": 0.2, "sad": -0.2, "calm": -0.15}.get(get(l, "mood", "calm"), 0.0)
        energy += w * min(1.0, max(0.0, inten + lift))
        total_w += w
    for k, v in BANTER_PRIOR.items():
        g[k] += v * len(lines)
    norm = math.sqrt(sum(v * v for v in g.values())) or 1.0
    return {"genres": {k: round(v / norm, 4) for k, v in g.items()}, "energy": round(energy / (total_w or 1.0), 3)}


def _cos(a: dict, b: dict) -> float:
    na = math.sqrt(sum(v * v for v in a.values())) or 1.0
    nb = math.sqrt(sum(v * v for v in b.values())) or 1.0
    return sum(a.get(k, 0.0) * b.get(k, 0.0) for k in GENRES) / (na * nb)


def score(track: Track, prof: dict, seconds: float, recent: list[str]) -> tuple[float, str]:
    fit = _cos(prof["genres"], track.moods)
    e = 1.0 - abs(track.energy - prof["energy"])
    s = fit + 0.25 * e
    if track.duration - track.start < seconds:  # it will loop: fine, but a single pass is nicer
        s -= 0.05
    if track.id in recent:
        s -= 0.35
    if track.viral:
        s += 0.15
    top = max(track.moods, key=lambda k: track.moods[k] * prof["genres"].get(k, 0.0)) if track.moods else "?"
    script_top = sorted(prof["genres"], key=lambda k: -prof["genres"][k])[:2]
    reason = f"{top} {fit:.2f}: script reads {' + '.join(script_top)}" + (" · viral" if track.viral else "")
    return round(s, 4), reason


def rank(lines, seconds: float, recent: list[str] | None = None, tracks: list[Track] | None = None,
         n: int = 3) -> list[dict]:
    prof = profile(lines)
    rows = []
    for t in (tracks if tracks is not None else library()):
        sc, why = score(t, prof, seconds, recent or [])
        rows.append({"track": t, "score": sc, "reason": why})
    rows.sort(key=lambda r: (-r["score"], r["track"].id))
    return rows[:n]


HISTORY = REPO / "projects" / ".music_history.json"


def recent_picks(project: Path, keep: int = 5) -> list[str]:
    rows = [r for r in _read(HISTORY) if r.get("project") != Path(project).name]
    return [r["id"] for r in rows[-keep:]]


def remember(project: Path, track_id: str) -> None:
    rows = [r for r in _read(HISTORY) if r.get("project") != Path(project).name]
    rows.append({"project": Path(project).name, "id": track_id})
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(rows[-50:], indent=1), encoding="utf-8")


def choose(project: Path, music: dict, lines, seconds: float) -> tuple[Track | None, list[dict]]:
    """The project's track: music.mode none -> None; track -> that id; auto -> ranked pick (music.pick shuffles
    through the top 3). Returns (track, top-3 ranking)."""
    mode = (music or {}).get("mode", "none" if not music else "auto")
    if mode == "none":
        return None, []
    top = rank(lines, seconds, recent_picks(project))
    if mode == "track":
        t = find(music.get("id", ""))
        if t is not None:
            return t, top
    if not top:
        return None, []
    return top[int(music.get("pick", 0)) % len(top)]["track"], top


# ---------- the bed ----------
@dataclass
class Bed:
    path: Path
    start: float = 0.0
    duration: float = 0.0   # of the source file; 0 = unknown (probed)
    vocals: bool = False
    volume: float = 0.5     # 0..1, 0.5 = the default level
    duck: bool = True


def bed_for(track: Track, music: dict) -> Bed:
    return Bed(track.path, track.start, track.duration, track.vocals, float(music.get("volume", 0.5)),
               bool(music.get("duck", True)))


def _probe(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def duck_expr(speech: list[tuple[float, float]], depth_db: float, ramp: float = 0.2) -> str:
    """ffmpeg volume expression: 1 in the pauses, `depth_db` while a line is spoken, with short ramps."""
    if not speech:
        return "1"
    parts = [f"clip(min((t-{a - ramp - 0.12:.3f})/{ramp},({b + 0.25 + ramp:.3f}-t)/{ramp}),0,1)" for a, b in speech]
    g = parts[0]
    for p in parts[1:]:
        g = f"max({g},{p})"
    floor = 10 ** (depth_db / 20)
    return f"1-{1 - floor:.4f}*{g}"


def build_bed(bed: Bed, seconds: float, speech: list[tuple[float, float]], end_at: float | None, dest: Path) -> Path:
    """Render the music bed: from the hook, looped with crossfades to `seconds`, loudness-set, ducked under the
    speech windows, lifted for the end card, faded in and out. Mono 48 kHz WAV."""
    dur = bed.duration or _probe(bed.path)
    start = min(bed.start, max(0.0, dur - 15.0))
    seg = max(1.0, dur - start)
    copies = 1 if seg >= seconds else 1 + math.ceil((seconds - seg) / max(1.0, seg - XFADE))
    ins = []
    for _ in range(copies):
        ins += ["-ss", f"{start:.3f}", "-i", str(bed.path)]
    chain = "[0:a]aresample=48000,aformat=channel_layouts=mono[a0];"
    for i in range(1, copies):
        chain += f"[{i}:a]aresample=48000,aformat=channel_layouts=mono[s{i}];"
        chain += f"[a{i - 1}][s{i}]acrossfade=d={XFADE}:c1=tri:c2=tri[a{i}];"
    base = VOCAL_BASE_LUFS if bed.vocals else BASE_LUFS
    gain = 20 * math.log10(max(0.05, bed.volume) / 0.5)  # the editor's slider around the default level
    depth = (VOCAL_DUCK_DB if bed.vocals else DUCK_DB) if bed.duck else 0.0
    post = (f"atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS,loudnorm=I={base}:TP=-6:LRA=11,aresample=48000,"
            f"volume={gain:.2f}dB,volume='{duck_expr(speech, depth)}':eval=frame")
    if bed.vocals and bed.duck and speech:  # pull the lyric band back under speech so the words don't collide
        on = "+".join(f"between(t,{a - 0.1:.3f},{b + 0.25:.3f})" for a, b in speech)
        post += f",equalizer=f=3000:t=q:w=1.4:g=-5:enable='{on}'"
    if end_at is not None and end_at < seconds:
        post += f",volume='if(gte(t,{end_at:.3f}),{10 ** (END_LIFT_DB / 20):.4f},1)':eval=frame"
    post += f",afade=t=in:d=0.6,afade=t=out:st={max(0.0, seconds - 1.2):.3f}:d=1.2"
    graph = chain + f"[a{copies - 1}]{post}[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", graph, "-map", "[out]", "-ac", "1",
                    "-ar", "48000", str(dest)], check=True)
    return Path(dest)


# ---------- owner tracks ----------
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "track"


def import_track(src: Path, title: str | None = None, moods: dict | None = None, vocals: bool = True,
                 viral_id: str | None = None, lib: Path | None = None) -> dict:
    """Copy an audio file into the owner's library, analyse it (duration, hook) and catalogue it."""
    lib = lib or LIB
    src = Path(src)
    mine = lib / "mine"
    mine.mkdir(parents=True, exist_ok=True)
    rows = _read(mine / "catalog.json")
    slot = next((s for s in _read(lib / "trending.json") if s["id"] == viral_id), None) if viral_id else None
    tid = viral_id or f"mine_{_slug(title or src.stem)}"
    taken = {r["id"] for r in rows if r["id"] != tid}
    base, k = tid, 2
    while tid in taken:
        tid, k = f"{base}_{k}", k + 1
    dest = mine / f"{tid}{src.suffix.lower()}"
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    info = analyze(dest, vocals)
    if not moods:
        moods = dict(slot.get("genres") or {}) if slot else {}
    if not moods:  # a guess from loudness; the owner fixes it in the editor
        moods = {"hype": 1.0, "wholesome": 0.4} if info["loudness"] > -12 else {"lofi": 1.0, "wholesome": 0.4}
    entry = {"id": tid, "title": title or (slot or {}).get("title") or src.stem,
             "artist": (slot or {}).get("artist", ""), "source": "mine", "file": f"mine/{dest.name}",
             "duration": info["duration"], "start": info["start"], "vocals": vocals, "viral": bool(slot),
             "energy": round(sum(GENRE_ENERGY[g] * w for g, w in moods.items()) / (sum(moods.values()) or 1), 3),
             "moods": moods, "licence": "owner", "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
             "note": (slot or {}).get("note", "")}
    rows = [r for r in rows if r["id"] != tid] + [entry]
    (mine / "catalog.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return entry


EDITABLE = ("title", "artist", "start", "vocals", "moods", "energy", "viral")


def update_track(track_id: str, patch: dict, lib: Path | None = None) -> dict:
    """Edit an owner track (tags, hook, vocals). Built-in tracks are read-only."""
    lib = lib or LIB
    path = lib / "mine" / "catalog.json"
    rows = _read(path)
    row = next((r for r in rows if r["id"] == track_id), None)
    if row is None:
        raise KeyError(f"{track_id}: not one of your tracks (built-in tracks can't be edited)")
    row.update({k: v for k, v in patch.items() if k in EDITABLE})
    if "moods" in patch and "energy" not in patch:
        m = row["moods"]
        row["energy"] = round(sum(GENRE_ENERGY.get(g, 0.5) * w for g, w in m.items()) / (sum(m.values()) or 1), 3)
    errs = validate([row])
    if errs:
        raise ValueError("; ".join(errs))
    path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return row


def remove_track(track_id: str, lib: Path | None = None) -> None:
    lib = lib or LIB
    path = lib / "mine" / "catalog.json"
    rows = _read(path)
    row = next((r for r in rows if r["id"] == track_id), None)
    if row is None:
        raise KeyError(f"{track_id}: not one of your tracks")
    (lib / row["file"]).unlink(missing_ok=True)
    path.write_text(json.dumps([r for r in rows if r["id"] != track_id], indent=1), encoding="utf-8")


def fetch_builtin(lib: Path | None = None) -> list[str]:
    """Download any missing built-in track from its recorded URL and check its sha256."""
    lib = lib or LIB
    got = []
    for e in _read(lib / "catalog.json"):
        dest = lib / e["file"]
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == e.get("sha256"):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(e["url"], headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=60).read()
        if e.get("sha256") and hashlib.sha256(data).hexdigest() != e["sha256"]:
            raise RuntimeError(f"{e['id']}: checksum mismatch, not saved")
        dest.write_bytes(data)
        got.append(e["id"])
    return got


def view(t: Track) -> dict:
    d = asdict(t)
    d["available"] = t.path.exists()
    return d
