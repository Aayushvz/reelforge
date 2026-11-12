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


# --- shotsav_top: the Shots-AV caption template (docs/prompts/03-shots-av-animation.md section 7) ---------------
AV_FONT = "Geist"
AV_FONT_PX = 46  # at 1080 wide
AV_LINE_CHARS = 22
AV_TOP = 0.08  # the caption block starts here (fraction of height); it ends above 0.12-0.14
AV_IN_FRAMES, AV_OUT_FRAMES, AV_CUT_LEAD = 4, 3, 3
AV_PLATE = "#1F1F1F"
AV_PLATE_ALPHA = 0.45
AV_CHAR_W = 0.56  # Geist Bold's average advance, as a share of the font size (for the plate's width)


def wrap_av(text: str, width: int = AV_LINE_CHARS) -> list[list[str]]:
    """Captions of at most two lines of `width` characters each: [[line, line], [line], ...]."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return [lines[i:i + 2] for i in range(0, len(lines), 2)] or [[""]]


def _round_rect(w: float, h: float, r: float) -> str:
    """An ASS drawing of a w x h rectangle with corner radius r, origin top-left."""
    k = r * 0.4477  # cubic approximation of a quarter circle
    return (f"m {r:.1f} 0 l {w - r:.1f} 0 b {w - k:.1f} 0 {w:.1f} {k:.1f} {w:.1f} {r:.1f} "
            f"l {w:.1f} {h - r:.1f} b {w:.1f} {h - k:.1f} {w - k:.1f} {h:.1f} {w - r:.1f} {h:.1f} "
            f"l {r:.1f} {h:.1f} b {k:.1f} {h:.1f} 0 {h - k:.1f} 0 {h - r:.1f} "
            f"l 0 {r:.1f} b 0 {k:.1f} {k:.1f} 0 {r:.1f} 0")


def _circle(d: float) -> str:
    return _round_rect(d, d, d / 2)


def ass_alpha_color(hex_rgb: str, opacity: float) -> tuple[str, str]:
    """(\\c colour, \\alpha) override tags for a colour at an opacity."""
    a = round(255 * (1.0 - opacity))
    return ass_color(hex_rgb).replace("&H00", "&H"), f"&H{a:02X}&"


def av_header(width: int, height: int) -> str:
    fs = round(AV_FONT_PX * width / 1080)
    return (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: AV,{AV_FONT},{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,0,0,1,0,0,8,40,40,0,1\n"
        "Style: Plate,Arial,10,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def av_events(placed: list[Placed], fps: int, total: float) -> list[tuple[float, float, list[str], str]]:
    """(start s, end s, lines, speaker) per caption: in AV_IN_FRAMES after the cut, out AV_OUT_FRAMES before the
    next cut. A line that needs more than two caption lines is shown in parts, timed by their share of letters."""
    out = []
    for i, p in enumerate(placed):
        cut = p.start - AV_CUT_LEAD / fps
        start = cut + AV_IN_FRAMES / fps
        if i + 1 < len(placed):
            end = placed[i + 1].start - (AV_CUT_LEAD + AV_OUT_FRAMES) / fps
        else:
            end = min(total, p.start + p.duration + 0.6)
        end = max(end, start + 0.3)
        parts = wrap_av(p.line.text)
        weights = [max(1, sum(len(x) for x in part)) for part in parts]
        t = start
        for part, wgt in zip(parts, weights):
            d = (end - start) * wgt / sum(weights)
            out.append((t, t + d, part, p.line.speaker))
            t += d
    return out


AV_LOWER = 0.70  # "lower" captions start here: above the bottom platform band (0.78 H)


def build_ass_shotsav(placed: list[Placed], perf: Performance, width: int, height: int, fps: int, total: float,
                      tints: dict[str, str] | None = None, plate: bool = True, position: str = "top") -> str:
    """The shotsav_top template: one caption line (or two) at a time, top centre, on a faint rounded ink plate,
    with a small dot in the speaker's colour."""
    fs = round(AV_FONT_PX * width / 1080)
    lh = round(fs * 1.18)
    x, y = width // 2, round(height * (AV_LOWER if position == "lower" else AV_TOP))
    pad_x, pad_y, radius, dot = round(fs * 0.55), round(fs * 0.28), round(10 * width / 1080), round(6 * width / 1080) + 4
    plate_c, plate_a = ass_alpha_color(AV_PLATE, AV_PLATE_ALPHA)
    rows = [av_header(width, height)]
    for start, end, lines, who in av_events(placed, fps, total):
        tw = max(len(line) for line in lines) * fs * AV_CHAR_W
        th = lh * len(lines)
        tint = (tints or {}).get(who)
        extra = (dot + round(fs * 0.3)) if tint else 0
        w, h = tw + 2 * pad_x + extra, th + 2 * pad_y
        left, top = x - w / 2, y - pad_y
        fade = f"\\fad({round(1000 * 3 / fps)},{round(1000 * 2 / fps)})"
        if plate:
            rows.append(f"Dialogue: 0,{ts(start)},{ts(end)},Plate,,0,0,0,,{{\\an7\\pos({left:.0f},{top:.0f})"
                        f"\\c{plate_c}\\alpha{plate_a}\\bord0\\shad0{fade}\\p1}}{_round_rect(w, h, radius)}{{\\p0}}")
        if tint:
            c, _ = ass_alpha_color(tint, 1.0)
            dy = top + pad_y + (lh - dot) / 2  # beside the first line
            rows.append(f"Dialogue: 1,{ts(start)},{ts(end)},Plate,,0,0,0,,{{\\an7\\pos({left + pad_x:.0f},{dy:.0f})"
                        f"\\c{c}\\bord0\\shad0{fade}\\p1}}{_circle(dot)}{{\\p0}}")
        body = "\\N".join(_clean(line) for line in lines)
        tx = x + extra / 2
        rows.append(f"Dialogue: 2,{ts(start)},{ts(end)},AV,,0,0,0,,{{\\an8\\pos({tx:.0f},{y:.0f}){fade}}}{body}")
    return "\n".join(rows) + "\n"
