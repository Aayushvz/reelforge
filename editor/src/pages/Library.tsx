// Asset library: every reusable asset in one place, with search, favourites and quick links.
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, Star, AudioLines, Music, Volume2, Image as ImageIcon, Captions, Shirt, Lightbulb } from "lucide-react";
import { CHARACTERS, ENVIRONMENTS, SUBTITLE_TEMPLATES, VOICES, WARDROBE, SLOTS, environment } from "@/data/catalog";
import { CharacterThumb, EnvThumb, SubtitleText } from "@/components/Thumbs";
import { FavButton } from "@/components/pickers";
import { AssetBadge, Badge, Empty } from "@/components/ui/Feedback";
import { useLibrary } from "@/stores/library";
import { api, fileUrl } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { outfitsFor } from "@/lib/outfits";

type Kind = "all" | "characters" | "outfits" | "environments" | "lighting" | "voices" | "subtitles" | "music" | "sfx" | "shots";
const KINDS: { id: Kind; label: string }[] = [
  { id: "all", label: "All" }, { id: "characters", label: "Characters" }, { id: "outfits", label: "Outfits" }, { id: "environments", label: "Environments" },
  { id: "lighting", label: "Lighting" }, { id: "voices", label: "Voices" }, { id: "subtitles", label: "Subtitles" }, { id: "music", label: "Music" },
  { id: "sfx", label: "Sound effects" }, { id: "shots", label: "Generated shots" },
];

type Item = { key: string; kind: Kind; name: string; meta: string; to?: string; media: React.ReactNode; badge?: React.ReactNode };

export function LibraryPage() {
  const [kind, setKind] = useState<Kind>("all");
  const [q, setQ] = useState("");
  const [favOnly, setFavOnly] = useState(false);
  const lib = useLibrary((s) => s.lib);
  const favs = lib.favorites ?? [];
  const nav = useNavigate();
  const [shots, setShots] = useState<{ p: ProjectSummary; still: string }[]>([]);

  useEffect(() => {
    api.projects().then(async (ps) => {
      const withStills = ps.filter((p) => p.thumb);
      const all = await Promise.all(withStills.map(async (p) => (await api.project(p.id)).files.stills.map((still) => ({ p, still }))));
      setShots(all.flat());
    }).catch(() => setShots([]));
  }, []);

  const items = useMemo<Item[]>(() => {
    const out: Item[] = [];
    for (const c of CHARACTERS) out.push({ key: `char:${c.id}`, kind: "characters", name: c.name, meta: c.vibe, to: `/characters/${c.id}`, media: <CharacterThumb character={c} />, badge: <AssetBadge status={c.status} /> });
    for (const c of CHARACTERS) for (const o of outfitsFor(c, lib)) out.push({ key: `outfit:${o.id}`, kind: "outfits", name: o.name, meta: `${c.name}${o.saved ? " · saved" : ""}`, to: `/characters/${c.id}`, media: <CharacterThumb character={c} outfit={o} />, badge: o.saved ? <Badge>Saved</Badge> : undefined });
    for (const e of ENVIRONMENTS) out.push({ key: `env:${e.id}`, kind: "environments", name: e.name, meta: `${e.category} · 3 lighting presets`, to: "/environments", media: <EnvThumb env={e} preset={e.presets[0]} />, badge: <AssetBadge status={e.status} /> });
    for (const e of ENVIRONMENTS) for (const p of e.presets) out.push({ key: `light:${e.id}:${p.id}`, kind: "lighting", name: p.name, meta: e.name, to: "/environments", media: <EnvThumb env={e} preset={p} /> });
    for (const s of lib.lighting ?? []) { const e = environment(s.environmentId); const p = e?.presets.find((x) => x.id === s.presetId); if (e && p) out.push({ key: `light:${s.id}`, kind: "lighting", name: s.name, meta: "Saved setup", to: "/environments", media: <EnvThumb env={e} preset={p} />, badge: <Badge>Saved</Badge> }); }
    for (const v of VOICES) out.push({ key: `voice:${v.id}`, kind: "voices", name: v.name, meta: v.tags.join(" · "), to: "/voices", media: <div className="lib-icon"><AudioLines size={22} /></div>, badge: <Badge>ElevenLabs</Badge> });
    for (const t of SUBTITLE_TEMPLATES) out.push({ key: `sub:${t.id}`, kind: "subtitles", name: t.name, meta: t.description, to: "/subtitles", media: <div className="sub-sample lib-sub"><SubtitleText s={t.style} text="Actually approved" active={1} scale={0.3} /></div> });
    for (const t of lib.subtitleTemplates ?? []) out.push({ key: `sub:${t.id}`, kind: "subtitles", name: t.name, meta: "Saved template", to: "/subtitles", media: <div className="sub-sample lib-sub"><SubtitleText s={t} text="Actually approved" active={1} scale={0.3} /></div>, badge: <Badge>Saved</Badge> });
    for (const s of shots) out.push({ key: `shot:${s.p.id}:${s.still}`, kind: "shots", name: s.still.replace(".png", "").replace("_", " "), meta: s.p.name, to: `/projects/${encodeURIComponent(s.p.id)}/render`, media: <img src={fileUrl(s.p.id, `out/stills/${s.still}`)} alt="" loading="lazy" /> });
    return out;
  }, [lib, shots]);

  const shown = items.filter((i) => (kind === "all" || i.kind === kind) && (!favOnly || favs.includes(i.key)) && (i.name + i.meta).toLowerCase().includes(q.toLowerCase()));
  const count = (k: Kind) => items.filter((i) => k === "all" || i.kind === k).length;

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head"><div className="grow"><h1 className="h1">Asset library</h1><div className="muted">Characters, outfits, sets, lighting, voices and caption styles you reuse across reels.</div></div></div>
        <div className="lib-layout">
          <nav className="lib-nav" aria-label="Asset types">
            {KINDS.map((k) => (
              <button key={k.id} className={`sb-link${kind === k.id ? " active" : ""}`} onClick={() => setKind(k.id)}>
                {iconFor(k.id)}<span className="grow" style={{ textAlign: "left" }}>{k.label}</span><span className="mono faint" style={{ fontSize: 11 }}>{count(k.id)}</span>
              </button>
            ))}
          </nav>
          <div className="col" style={{ gap: 16, minWidth: 0 }}>
            <div className="toolbar" style={{ marginBottom: 0 }}>
              <div className="search grow"><Search size={14} /><input className="input" placeholder="Search assets" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: "100%" }} /></div>
              <button className="chip" aria-pressed={favOnly} onClick={() => setFavOnly(!favOnly)}><Star size={12} fill={favOnly ? "currentColor" : "none"} />Favourites</button>
            </div>
            {(kind === "music" || kind === "sfx") ? (
              <Empty icon={kind === "music" ? <Music size={18} /> : <Volume2 size={18} />} title={`No ${kind === "music" ? "music" : "sound effects"} yet`}
                action={<Link className="btn" to="/editor">Open the editor</Link>}>
                Nothing is bundled yet. Import audio into a project's media bin in the editor; a shared audio library is planned with music and foley in M2.
              </Empty>
            ) : shown.length === 0 ? (
              <Empty icon={<Search size={18} />} title="Nothing matches">{favOnly ? "Star assets to collect them here." : kind === "shots" ? "Stills from your renders appear here." : "Try another search."}</Empty>
            ) : (
              <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: 12 }}>
                {shown.map((i) => (
                  <div key={i.key} className="card interactive asset-card" role="button" tabIndex={0} onClick={() => i.to && nav(i.to)} onKeyDown={(e) => e.key === "Enter" && i.to && nav(i.to)}>
                    <div className="thumb">{i.media}<div className="over">{i.badge}<span className="fav"><FavButton k={i.key} /></span></div></div>
                    <div className="body"><span className="title ellipsis">{i.name}</span><span className="meta ellipsis">{i.meta}</span></div>
                  </div>
                ))}
              </div>
            )}
            {kind === "outfits" && <div className="hint">{WARDROBE.length} wardrobe items across {SLOTS.length} slots. Build and save outfits on a character's page.</div>}
            {kind === "characters" && <div className="hint">Concept cards until the characters are built in Blender.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

function iconFor(k: Kind) {
  const s = 15;
  return { all: <Star size={s} />, characters: <Shirt size={s} />, outfits: <Shirt size={s} />, environments: <ImageIcon size={s} />, lighting: <Lightbulb size={s} />, voices: <AudioLines size={s} />, subtitles: <Captions size={s} />, music: <Music size={s} />, sfx: <Volume2 size={s} />, shots: <ImageIcon size={s} /> }[k];
}
