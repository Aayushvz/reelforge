import { useEffect } from "react";
import { Check, X, RefreshCw, Keyboard, FolderTree } from "lucide-react";
import { useSystem, pipelineReady } from "@/stores/system";
import { useUI } from "@/stores/ui";
import { Badge, Spinner } from "@/components/ui/Feedback";
import { useLibrary } from "@/stores/library";

export function SettingsPage() {
  const status = useSystem((s) => s.status);
  const load = useSystem((s) => s.load);
  const lib = useLibrary((s) => s.lib);
  useEffect(() => { void load(); }, [load]);
  const rows: [boolean | undefined, string, React.ReactNode][] = [
    [status?.reelforge, "reelforge pipeline", <>In the repo: <code>python -m venv .venv</code>, then <code>.venv/Scripts/python -m pip install -e ".[dev,align]"</code></>],
    [status?.blender, "Blender 4.5 LTS", <>Portable build in <code>tools/blender-4.5/</code>, its executable path in <code>tools/blender_path.txt</code>. The download is about 400 MB.</>],
    [status?.ffmpeg, "ffmpeg and ffprobe", <>Installed and on PATH.</>],
    [status?.assetsBuilt, "Base assets built", <>Run <code>reelforge build-assets</code> once Blender is set up.</>],
    [status?.elevenlabsKey, "ElevenLabs API key (optional)", <>Not needed. Voices are generated in the ElevenLabs web app and imported as mp3s.</>],
  ];
  return (
    <div className="page">
      <div className="page-inner" style={{ maxWidth: 860 }}>
        <div className="page-head"><div className="grow"><h1 className="h1">Settings</h1><div className="muted">Render engine status, shortcuts and where your work is stored.</div></div></div>
        <section className="panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14, marginBottom: 16 }}>
          <div className="row"><h2 className="h2 grow">Render engine</h2>
            {status && <Badge tone={pipelineReady(status) ? "ok" : "warn"} pip>{pipelineReady(status) ? "Ready" : "Not set up"}</Badge>}
            <button className="btn btn-sm" onClick={() => void load()}><RefreshCw size={12} />Check again</button></div>
          {!status ? <div className="row"><Spinner /><span className="muted">Checking…</span></div> : rows.map(([ok, label, help]) => (
            <div key={label} className="row" style={{ alignItems: "flex-start", gap: 12 }}>
              <span style={{ width: 20, height: 20, borderRadius: 10, display: "grid", placeItems: "center", flex: "none", background: ok ? "var(--ok-soft)" : "var(--bg-3)", color: ok ? "var(--ok)" : "var(--text-3)" }}>{ok ? <Check size={12} /> : <X size={12} />}</span>
              <div className="col" style={{ gap: 2 }}><span>{label}</span><span className="meta settings-help">{help}</span></div>
            </div>
          ))}
          <div className="hint">The editor only reads these. It never installs or downloads anything on its own.</div>
        </section>
        <section className="panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          <div className="row"><FolderTree size={16} className="faint" /><h2 className="h2 grow">Storage</h2></div>
          <dl className="kv">
            <dt>Repository</dt><dd className="mono meta">{status?.repo ?? "…"}</dd>
            <dt>New projects</dt><dd className="mono meta">projects/&lt;name&gt;/ · performance.json, editor.json, media/, out/</dd>
            <dt>Samples</dt><dd className="mono meta">samples/ (protected from deletion)</dd>
            <dt>Library</dt><dd className="mono meta">projects/library.json · {(lib.favorites ?? []).length} favourites, {(lib.subtitleTemplates ?? []).length} saved subtitle styles, {(lib.outfits ?? []).length} outfits, {(lib.lighting ?? []).length} lighting setups</dd>
          </dl>
        </section>
        <section className="panel" style={{ padding: 20 }}>
          <div className="row"><Keyboard size={16} className="faint" /><h2 className="h2 grow">Keyboard shortcuts</h2><button className="btn btn-sm" onClick={() => useUI.getState().setShortcutsOpen(true)}>Show all <span className="kbd">?</span></button></div>
        </section>
      </div>
    </div>
  );
}
