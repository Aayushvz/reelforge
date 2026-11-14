"""Draft a cover image for a rendered reel: a punchy two-line headline and a good frame.

The editor's Thumbnail Generator draws the cover itself (browser canvas); this module only picks
the words and the frame, deterministically, from performance.json and out/render_plan.json.
Reference covers: "FIX THE / NAVBAR." and "LOGO / BIGGER." over a close-up of the hero.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# imperative verbs that open a "do X to the Y" headline ("fix the navbar")
VERBS = {
    "fix", "make", "change", "add", "remove", "delete", "ship", "build", "move", "update", "redo", "undo",
    "center", "centre", "align", "rename", "refactor", "deploy", "test", "push", "merge", "break", "touch",
    "redesign", "resize", "rewrite", "clean", "kill", "drop", "cut", "save", "launch", "hide", "show", "swap",
    "replace", "revert", "style", "animate", "format", "translate", "finish", "check", "send", "post", "stop",
}
DETS = {"the", "a", "an", "my", "this", "that", "our", "your", "those", "these", "his", "her", "their", "its"}
# how a thing ended up: "the logo bigger", "the homepage broken", "the animations are gone"
STATES = {
    "bigger", "smaller", "larger", "faster", "slower", "darker", "brighter", "louder", "quieter", "bolder",
    "cleaner", "simpler", "better", "worse", "longer", "shorter", "wider", "thinner", "thicker", "sharper",
    "softer", "higher", "lower", "broken", "gone", "wrong", "missing", "dead", "down", "messy", "ugly", "off",
    "weird", "right", "fixed", "done", "perfect", "blurry", "crooked", "late", "empty", "red", "huge", "tiny",
}
LINKS = {"is", "are", "was", "were", "got", "gets", "looks", "look", "seems", "feels", "be", "stays", "go", "went"}
STOP = {
    "i", "me", "my", "you", "your", "we", "our", "it", "its", "he", "she", "they", "them", "the", "a", "an",
    "and", "or", "but", "so", "to", "of", "in", "on", "at", "for", "with", "is", "are", "was", "were", "be",
    "been", "am", "do", "did", "does", "just", "that", "this", "those", "these", "what", "why", "how", "when",
    "who", "can", "could", "would", "should", "will", "i'll", "i've", "i'm", "you're", "it's", "don't", "not",
    "no", "yes", "oh", "ok", "okay", "um", "uh", "like", "really", "very", "only", "all", "too", "also",
    "asked", "ask", "said", "say", "then", "there", "here", "now", "one", "some", "any", "get", "got", "about",
    "from", "into", "out", "up", "if", "as", "by", "has", "have", "had", "his", "her", "their", "wait", "well",
}
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _strip_vocative(text: str, names: set[str]) -> str:
    """Drop a leading "Claude," / "Hey Claude..." so the name never becomes the headline."""
    t = text.strip()
    m = re.match(r"^\s*(?:hey|hi|ok|okay|so|um|look|listen)?[,\s]*([A-Z][\w\-]*)\s*(?:,|\.{2,}|…|!)\s*", t)
    if m and (m.group(1).lower() in names or len(m.group(1)) > 2):
        t = t[m.end():]
    return t


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]


def _words(sentence: str) -> list[str]:
    return [w.lower().strip("'-") for w in WORD.findall(sentence)]


def _lines(a: list[str], b: list[str]) -> list[str]:
    return [" ".join(a).upper(), " ".join(b).upper().rstrip(".!?") + "."]


def candidates(text: str, names: set[str] = frozenset()) -> list[tuple[list[str], str]]:
    """Every headline the rules find in one spoken line, best first: ([line1, line2], source sentence)."""
    names = {n.lower() for n in names}
    out: list[tuple[list[str], str]] = []
    body = _strip_vocative(text, names)
    sents = _sentences(body) or [body]
    # rule 1, then rule 2, across the whole line: a verb phrase beats a state phrase
    for rule in (1, 2):
        for s in sents:
            w = _words(s)
            for i in range(len(w)):
                if rule == 1 and w[i] in VERBS and i + 2 < len(w) and w[i + 1] in DETS:
                    noun = w[i + 2]
                    if noun not in STOP and noun not in names:
                        out.append((_lines([w[i], w[i + 1]], [noun]), s))
                elif rule == 2 and w[i] in DETS:
                    j = i + 1
                    # optional adjective before the noun ("the entire homepage", "those little details")
                    for noun_at in (j, j + 1):
                        if noun_at >= len(w) or w[noun_at] in STOP or w[noun_at] in names:
                            continue
                        k = noun_at + 1
                        if k < len(w) and w[k] in LINKS:
                            k += 1
                        if k < len(w) and w[k] in STATES and w[noun_at] not in STATES:
                            out.append((_lines([w[noun_at]], [w[k]]), s))
                            break
    if not out:  # rule 3: the two longest content words, kept in spoken order
        for s in sents:
            content = [(i, x) for i, x in enumerate(_words(s)) if x not in STOP and x not in names and len(x) > 2]
            if len(content) >= 2:
                best = sorted(sorted(content, key=lambda p: -len(p[1]))[:2])
                out.append((_lines([best[0][1]], [best[1][1]]), s))
                break
    seen, uniq = set(), []
    for h, s in out:
        if tuple(h) not in seen:
            seen.add(tuple(h))
            uniq.append((h, s))
    return uniq


def headline(text: str, names: set[str] = frozenset()) -> list[str] | None:
    c = candidates(text, names)
    return c[0][0] if c else None


def _hero(perf: dict) -> str:
    chars = list((perf.get("characters") or {}).keys())
    return "me" if "me" in chars or not chars else chars[0]


def pick_frames(plan: dict, n: int = 3, hero: str = "me") -> list[dict]:
    """Best hero shots for a cover: biggest face, speaking, pushing in. One frame per shot, 40% in."""
    scored = []
    for i, s in enumerate(plan.get("shots") or []):
        if s.get("subject") != hero:
            continue
        start, end = int(s.get("start_frame", 0)), int(s.get("end_frame", 0))
        if end - start < 6:
            continue
        fr = s.get("framing") or {}
        eyes = fr.get("eyes")
        # the face must be in the picture: inserts (hands, keyboard) push the eyes out of frame
        if eyes is not None and not 0.15 <= float(eyes) <= 0.85 or "hands" in str(s.get("angle", "")):
            continue
        head = float(fr.get("head") or 0.0)
        push = float((s.get("move_params") or {}).get("amount") or 0.0) if s.get("move") in ("push_in", "slow_zoom") else 0.0
        score = head + (0.3 if s.get("speaker") == hero else 0.0) + 0.1 * min(1.0, push * 10)
        scored.append((score, i, start + round((end - start) * 0.4)))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [{"shot": i, "frame": f, "score": round(sc, 3)} for sc, i, f in scored[:n]]


def find_video(project: Path) -> Path | None:
    out = project / "out"
    preferred = out / "final_9x16.mp4"
    if preferred.exists():
        return preferred
    finals = sorted(p for p in out.glob("final_*.mp4") if not p.stem.endswith("_share"))
    return finals[0] if finals else None


def draft(project: Path, n: int = 3) -> dict:
    project = Path(project)
    perf = json.loads((project / "performance.json").read_text(encoding="utf-8"))
    plan_file = project / "out" / "render_plan.json"
    plan = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else {}
    video = find_video(project)
    if video is None:
        raise FileNotFoundError("no final video in out/")
    fps = float(plan.get("fps") or perf.get("fps") or 30)
    hero = _hero(perf)
    names = {"claude", "chatgpt", "gpt", "figma", "nova", "siri", "alexa", "gemini", "copilot", "bro", "dude", "man"}
    names |= {str(k).lower() for k in (perf.get("characters") or {})}

    heads: list[tuple[list[str], str]] = []
    lines = perf.get("lines") or []
    # the hero's lines first (the hook), then everyone else's
    for line in sorted(lines, key=lambda l: 0 if l.get("speaker") == hero else 1):
        text = str(line.get("text", "")).strip()
        for h, src in candidates(text, names):
            if all(h != x[0] for x in heads):
                # the pill carries the spoken line; a long line keeps just the sentence the headline came from
                heads.append((h, text if len(text) <= 80 else src))
    if not heads:
        heads = [(["WAIT FOR", "IT."], "")]

    frames = pick_frames(plan, n, hero) or [{"shot": None, "frame": round(fps), "score": 0.0}]
    # the rendered frames are clean: no burned-in captions, which would fight the cover's own text
    clean = project / "out" / "frames"
    has_clean = (clean / "0001.png").exists()
    variants = []
    for i in range(min(n, max(len(heads), len(frames)))):
        h, src = heads[i % len(heads)]
        f = frames[i % len(frames)]
        v = {"headline": h, "caption": src, "frame": f["frame"], "time": round(f["frame"] / fps, 3), "shot": f["shot"]}
        still = clean / f"{f['frame'] + 1:04d}.png"
        if has_clean and still.exists():
            v["still"] = still.relative_to(project).as_posix()
        variants.append(v)
    w, hgt = (plan.get("resolution") or [1080, 1920])[:2]
    out = {"video": video.relative_to(project).as_posix(), "fps": fps, "width": w, "height": hgt, "variants": variants}
    if has_clean:
        out["frames"] = "out/frames"  # frame N is out/frames/{N+1:04d}.png
    return out


def write_draft(project: Path) -> dict:
    d = draft(project)
    (Path(project) / "out" / "cover.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d
