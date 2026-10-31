from __future__ import annotations

from .alignment import Word, words_from_chars
from .schema import Performance
from .timeline import Placed

SAFE_ZONES: dict[str, tuple[int, int]] = {  # (top, bottom) px kept clear by the platform UI
    "9:16": (220, 420), "16:9": (60, 60), "3:4": (80, 120), "1:1": (60, 60),
}
HOLD = 0.25
POP = r"{\fscx80\fscy80\t(0,80,\fscx108\fscy108)\t(80,160,\fscx100\fscy100)}"
PUNCH_POP = (r"{\fscx80\fscy80\t(0,100,\fscx130\fscy130)\t(100,200,\fscx118\fscy118)"
             r"\t(0,110,\frz-4)\t(110,220,\frz3)\t(220,320,\frz0)}")
PUNCH_HOLD = r"{\fscx118\fscy118}"


def ass_color(hex_rgb: str) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}&"


def ts(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def group_words(words: list[Word], max_words: int = 4, gap: float = 0.3) -> list[list[Word]]:
    groups: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        if cur and (len(cur) >= max_words or w.start - cur[-1].end > gap):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w.text[-1] in ".!?,;:":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def _ratio_for(width: int, height: int) -> str:
    r = width / height
    return min(SAFE_ZONES, key=lambda k: abs(eval_ratio(k) - r))


def eval_ratio(key: str) -> float:
    a, b = key.split(":")
    return int(a) / int(b)


def ass_header(width: int, height: int) -> str:
    fs = round(min(height * 0.042, width * 0.075))
    return (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Main,Segoe UI Black,{fs},&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,"
        f"-1,0,0,0,100,100,0,0,1,{max(3, fs // 12)},{max(2, fs // 20)},8,60,60,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def _clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")")


def build_ass(placed: list[Placed], perf: Performance, width: int, height: int) -> str:
    top, _ = SAFE_ZONES[_ratio_for(width, height)]
    x, y = width // 2, top + int(height * 0.04)
    lines = [ass_header(width, height)]
    all_groups: list[tuple[Placed, list[Word]]] = []
    for p in placed:
        words = [Word(w.text, p.start + w.start, p.start + w.end) for w in words_from_chars(p.voiced.chars)]
        all_groups += [(p, g) for g in group_words(words)]
    for gi, (p, group) in enumerate(all_groups):
        ch = perf.characters[p.line.speaker]
        base, hi = ass_color(ch.caption_color), ass_color(ch.highlight_color)
        next_start = all_groups[gi + 1][1][0].start if gi + 1 < len(all_groups) else None
        for k, w in enumerate(group):
            start = w.start
            end = group[k + 1].start if k + 1 < len(group) else w.end + HOLD
            if next_start is not None:
                end = min(end, next_start)
            body = " ".join(
                f"{{\\c{hi}}}{_clean(o.text)}{{\\c{base}}}" if j == k else _clean(o.text)
                for j, o in enumerate(group))
            if k == 0:
                fx = PUNCH_POP if p.line.punchline else POP
            else:
                fx = PUNCH_HOLD if p.line.punchline else ""
            lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Main,,0,0,0,,"
                         f"{{\\an8\\pos({x},{y})\\c{base}}}{fx}{body}")
    return "\n".join(lines) + "\n"
