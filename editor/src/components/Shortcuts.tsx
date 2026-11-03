import { Keyboard } from "lucide-react";
import { Dialog } from "./ui/Overlay";
import { useUI } from "@/stores/ui";

const mod = navigator.platform.toLowerCase().includes("mac") ? "⌘" : "Ctrl";
export const SHORTCUTS: { group: string; items: [string, string][] }[] = [
  { group: "Playback", items: [["Space", "Play / pause"], ["J / K / L", "Back 1s / pause / forward 1s"], ["← / →", "Step one frame"], ["Shift ← / →", "Step one second"], ["Home / End", "Go to start / end"], ["↑ / ↓", "Previous / next shot"]] },
  { group: "Editing", items: [["S", "Split at playhead"], ["Delete", "Delete selected clips"], [`${mod} D`, "Duplicate selected clips"], [`${mod} Z`, "Undo"], [`${mod} Shift Z`, "Redo"], [`${mod} S`, "Save now"], [`${mod} A`, "Select all clips"], ["Esc", "Clear selection"]] },
  { group: "Timeline", items: [["= / -", "Zoom in / out"], ["0", "Zoom to fit"], ["N", "Toggle snapping"]] },
  { group: "Workspace", items: [["[", "Toggle sidebar"], ["F", "Maximise preview"], ["?", "Show shortcuts"]] },
];

export function ShortcutsDialog() {
  const open = useUI((s) => s.shortcutsOpen);
  const setOpen = useUI((s) => s.setShortcutsOpen);
  if (!open) return null;
  return (
    <Dialog title="Keyboard shortcuts" icon={<Keyboard size={16} className="faint" />} onClose={() => setOpen(false)} wide>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "var(--s-5)" }}>
        {SHORTCUTS.map((g) => (
          <div key={g.group} className="col" style={{ gap: 6 }}>
            <div className="eyebrow" style={{ marginBottom: 4 }}>{g.group}</div>
            {g.items.map(([k, label]) => (
              <div key={label} className="row" style={{ justifyContent: "space-between", height: 26 }}>
                <span className="muted">{label}</span>
                <span className="row" style={{ gap: 4 }}>{k.split(" ").filter((x) => x !== "/").map((p, i) => <span key={i} className="kbd">{p}</span>)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Dialog>
  );
}
