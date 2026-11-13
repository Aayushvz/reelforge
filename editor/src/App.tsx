import { Route, Routes, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { Toasts } from "./components/ui/Overlay";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ShortcutsDialog } from "./components/Shortcuts";
import { useUI } from "./stores/ui";
import { useLibrary } from "./stores/library";
import { CreatePage } from "./pages/Create";
import { ProjectsPage } from "./pages/Projects";
import { EditorHome } from "./pages/EditorHome";
import { EditorPage } from "./pages/editor/Editor";
import { LibraryPage } from "./pages/Library";
import { CharactersPage } from "./pages/Characters";
import { EnvironmentsPage } from "./pages/Environments";
import { SubtitlesPage } from "./pages/Subtitles";
import { VoicesPage } from "./pages/Voices";
import { RenderPage } from "./pages/Render";
import { ExportPage } from "./pages/Export";
import { SettingsPage } from "./pages/Settings";
import { NotFound } from "./pages/NotFound";
import { ShotsAvListPage } from "./pages/shotsav/ShotsAvList";
import { ShotsAvWorkspace } from "./pages/shotsav/ShotsAvWorkspace";

export function App() {
  const loc = useLocation();
  const inEditor = /^\/editor\/.+/.test(loc.pathname);
  const loadLibrary = useLibrary((s) => s.load);
  useEffect(() => { void loadLibrary(); }, [loadLibrary]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement | null)?.closest?.("input, textarea, select, [contenteditable]")) return;
      if (e.key === "[" && !e.ctrlKey && !e.metaKey) useUI.getState().toggleSidebar();
      if (e.key === "?" ) useUI.getState().setShortcutsOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="app">
      {!inEditor && <Sidebar />}
      <main className="main">
        <ErrorBoundary key={loc.pathname}>
        <Routes>
          <Route path="/" element={<CreatePage />} />
          <Route path="/shots-av" element={<ShotsAvListPage />} />
          <Route path="/shots-av/:id" element={<ShotsAvWorkspace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id/render" element={<RenderPage />} />
          <Route path="/projects/:id/export" element={<ExportPage />} />
          <Route path="/editor" element={<EditorHome />} />
          <Route path="/editor/:id" element={<EditorPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/characters" element={<CharactersPage />} />
          <Route path="/characters/:cid" element={<CharactersPage />} />
          <Route path="/environments" element={<EnvironmentsPage />} />
          <Route path="/subtitles" element={<SubtitlesPage />} />
          <Route path="/voices" element={<VoicesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        </ErrorBoundary>
      </main>
      <Toasts />
      <ShortcutsDialog />
    </div>
  );
}
