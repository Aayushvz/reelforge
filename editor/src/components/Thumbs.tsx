// Placeholder artwork for assets that have no render yet. Each one is drawn from the asset's
// real data (lighting colours, outfit colours) so it carries information, and every card
// that uses one says it's a placeholder until the Blender render exists.
import { useId, type CSSProperties } from "react";
import { wardrobeItem, type Character, type Environment, type LightingPreset, type Outfit } from "@/data/catalog";
import type { SubtitleStyle } from "@/lib/types";

const LAYOUT: Record<string, "windows" | "lanterns" | "horizon" | "tiles" | "room"> = {
  "night-city-desk": "windows", bedroom: "room", rooftop: "horizon", cafe: "windows", "lantern-street": "lanterns",
  subway: "tiles", campus: "room", office: "windows", "night-mart": "tiles", pier: "horizon",
};

export function EnvThumb({ env, preset, style }: { env: Environment; preset: LightingPreset; style?: CSSProperties }) {
  const id = useId().replace(/:/g, "");
  const layout = LAYOUT[env.id] ?? "room";
  return (
    <svg viewBox="0 0 160 100" preserveAspectRatio="xMidYMid slice" style={{ display: "block", width: "100%", height: "100%", ...style }} aria-hidden>
      <defs>
        <radialGradient id={`k${id}`} cx="0.28" cy="0.62" r="0.6"><stop offset="0" stopColor={preset.key} stopOpacity="0.55" /><stop offset="1" stopColor={preset.key} stopOpacity="0" /></radialGradient>
        <radialGradient id={`g${id}`} cx="0.72" cy="0.45" r="0.35"><stop offset="0" stopColor={preset.glow} stopOpacity="0.7" /><stop offset="1" stopColor={preset.glow} stopOpacity="0" /></radialGradient>
        <linearGradient id={`s${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={preset.sky} /><stop offset="1" stopColor="#050505" /></linearGradient>
      </defs>
      <rect width="160" height="100" fill={`url(#s${id})`} />
      {layout === "windows" && Array.from({ length: 18 }, (_, i) => (
        <rect key={i} x={16 + (i % 6) * 22} y={14 + Math.floor(i / 6) * 16} width="14" height="9" rx="1" fill={preset.glow} opacity={0.08 + ((i * 37) % 10) / 40} />
      ))}
      {layout === "lanterns" && Array.from({ length: 9 }, (_, i) => (
        <g key={i}><line x1={10 + i * 18} y1="0" x2={10 + i * 18} y2={16 + (i % 3) * 6} stroke={preset.rim} strokeOpacity=".3" strokeWidth=".6" />
          <ellipse cx={10 + i * 18} cy={20 + (i % 3) * 6} rx="4" ry="5" fill={preset.glow} opacity=".75" /></g>
      ))}
      {layout === "horizon" && <>
        <path d="M0 62 L12 62 L12 44 L22 44 L22 54 L34 54 L34 36 L44 36 L44 58 L58 58 L58 48 L70 48 L70 62 L92 62 L92 40 L100 40 L100 30 L108 30 L108 52 L124 52 L124 46 L138 46 L138 62 L160 62 L160 100 L0 100 Z" fill="#000" opacity=".55" />
        {Array.from({ length: 14 }, (_, i) => <circle key={i} cx={6 + i * 11.5} cy={20 + Math.sin(i) * 3} r=".9" fill={preset.glow} opacity=".9" />)}
      </>}
      {layout === "tiles" && Array.from({ length: 40 }, (_, i) => (
        <rect key={i} x={(i % 10) * 16} y={8 + Math.floor(i / 10) * 12} width="15" height="11" fill={preset.key} opacity={0.04 + (i % 3) * 0.015} />
      ))}
      {layout === "room" && <>
        <rect x="96" y="14" width="44" height="34" rx="1.5" fill={preset.sky} stroke={preset.key} strokeOpacity=".25" />
        <rect x="14" y="20" width="30" height="40" fill={preset.key} opacity=".06" />
      </>}
      <rect width="160" height="100" fill={`url(#k${id})`} />
      <rect width="160" height="100" fill={`url(#g${id})`} />
      <path d="M0 74 L160 70 L160 100 L0 100 Z" fill="#000" opacity=".6" />
      <line x1="0" y1="74" x2="160" y2="70" stroke={preset.rim} strokeOpacity=".35" strokeWidth=".6" />
    </svg>
  );
}

export function CharacterThumb({ character, outfit, style, pose = "bust" }: { character: Character; outfit?: Outfit; style?: CSSProperties; pose?: "bust" | "full" }) {
  const id = useId().replace(/:/g, "");
  const items = outfit?.items ?? character.outfits[0]?.items ?? {};
  const colors = outfit?.colors ?? {};
  const col = (slot: keyof typeof items) => colors[slot] ?? wardrobeItem(items[slot] ?? "")?.color;
  const top = col("outer") ?? col("top") ?? "#3a3a3e";
  const inner = col("top") ?? top;
  const bottom = col("bottom") ?? "#2a2a2c";
  const shoes = col("shoes") ?? "#ddd";
  const skin = character.tone;
  const female = character.gender === "female";
  const hair = "#141214";
  if (pose === "full") {
    return (
      <svg viewBox="0 0 100 160" style={{ display: "block", width: "100%", height: "100%", ...style }} aria-hidden>
        <rect width="100" height="160" fill="#121214" />
        <ellipse cx="50" cy="150" rx="26" ry="4" fill="#000" opacity=".5" />
        <rect x="38" y="96" width="10" height="50" rx="4" fill={bottom} /><rect x="52" y="96" width="10" height="50" rx="4" fill={bottom} />
        <rect x="35" y="144" width="14" height="6" rx="3" fill={shoes} />
        <rect x="51" y="144" width="14" height="6" rx="3" fill={shoes} />
        <path d="M32 56 Q50 48 68 56 L66 100 L34 100 Z" fill={top} />
        <path d="M44 54 L50 66 L56 54 Z" fill={inner} />
        <rect x="46" y="44" width="8" height="10" rx="3" fill={skin} />
        <ellipse cx="50" cy="32" rx="12" ry="14" fill={skin} />
        <path d={female ? "M37 32 Q36 14 50 15 Q64 14 63 32 L64 52 Q60 40 60 28 Q50 22 40 28 Q40 40 36 52 Z" : "M38 30 Q38 15 50 16 Q62 15 62 30 Q58 22 50 22 Q42 22 38 30 Z"} fill={hair} />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 120 120" style={{ display: "block", width: "100%", height: "100%", ...style }} aria-hidden>
      <defs><radialGradient id={`r${id}`} cx="0.5" cy="0.35" r="0.7"><stop offset="0" stopColor="#26262a" /><stop offset="1" stopColor="#111113" /></radialGradient></defs>
      <rect width="120" height="120" fill={`url(#r${id})`} />
      <path d="M18 120 Q22 86 60 82 Q98 86 102 120 Z" fill={top} />
      <path d="M50 84 L60 100 L70 84 Z" fill={inner} />
      <rect x="53" y="66" width="14" height="20" rx="6" fill={skin} />
      <ellipse cx="60" cy="50" rx="20" ry="23" fill={skin} />
      <path d={female ? "M38 52 Q34 22 60 22 Q86 22 82 52 L86 92 Q76 74 78 46 Q60 34 42 46 Q44 74 34 92 Z" : "M40 46 Q40 22 60 23 Q80 22 80 46 Q74 34 60 34 Q46 34 40 46 Z"} fill={hair} />
      <path d="M40 52 Q38 44 44 40" stroke="#fff" strokeOpacity=".08" strokeWidth="3" fill="none" />
    </svg>
  );
}

// Caption text rendered with a subtitle style. `active` is the index of the spoken word.
export function SubtitleText({ s, text, active = -1, scale = 1, punch }: { s: SubtitleStyle; text: string; active?: number; scale?: number; punch?: boolean }) {
  const ws = (s.uppercase ? text.toUpperCase() : text).split(" ").filter(Boolean);
  const size = s.size * scale;
  const outline = s.outline * scale;
  const shadow = s.shadow * scale;
  const textShadow = [
    outline ? `0 0 ${outline}px #000, ${outline / 2}px ${outline / 2}px 0 #000, -${outline / 2}px -${outline / 2}px 0 #000, ${outline / 2}px -${outline / 2}px 0 #000, -${outline / 2}px ${outline / 2}px 0 #000` : "",
    shadow ? `0 ${shadow}px ${shadow * 2}px rgba(0,0,0,.7)` : "",
  ].filter(Boolean).join(", ") || "none";
  const bar = s.background && s.background !== "highlight";
  return (
    <span style={{
      display: "inline-block", maxWidth: "100%", fontFamily: `"${s.font}", var(--font-sans)`, fontWeight: s.weight, fontSize: size,
      fontStyle: s.italic ? "italic" : "normal", lineHeight: s.lineSpacing, textAlign: s.align, color: s.color, textShadow,
      background: bar ? s.background! : "transparent", padding: bar ? `${size * 0.12}px ${size * 0.3}px` : 0, borderRadius: bar ? 4 * scale : 0,
      transform: punch ? "scale(1.12)" : undefined, transition: "transform 160ms var(--ease)", letterSpacing: s.font === "Anton" ? "0.01em" : "-0.01em",
    }}>
      {ws.map((w, i) => {
        const on = i === active || (s.animation === "karaoke" && i <= active);
        const block = s.background === "highlight" && i === active;
        return (
          <span key={i} style={{
            color: on ? s.highlight : undefined,
            background: block ? s.highlight : undefined, padding: block ? `0 ${size * 0.12}px` : undefined, borderRadius: block ? 3 * scale : undefined,
            ...(block ? { color: "#111", textShadow: "none" } : {}),
          }}>{w}{i < ws.length - 1 ? " " : ""}</span>
        );
      })}
    </span>
  );
}
