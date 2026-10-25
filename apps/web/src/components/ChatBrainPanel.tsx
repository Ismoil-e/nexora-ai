"use client";

import { useRef, useState } from "react";

export interface BrainSource {
  id: string;
  name: string;
  detail?: string;
}

interface BrainGraphNode {
  id: string;
  name: string;
  category: "Foydalanilgan manba" | "Yuklangan fayl";
  kind: "source" | "upload";
}

function connectionPath(x: number, y: number) {
  const dx = x - 50;
  const dy = y - 50;
  return `M 50 50 C ${50 + dx * 0.32} ${50 + dy * 0.36}, ${x - dx * 0.18} ${y - dy * 0.14}, ${x} ${y}`;
}

interface ChatBrainPanelProps {
  sources: BrainSource[];
  uploadedFiles: string[];
  onClose: () => void;
}

export default function ChatBrainPanel({
  sources,
  uploadedFiles,
  onClose,
}: ChatBrainPanelProps) {
  const graphNodes: BrainGraphNode[] = [
    ...sources.map((source) => ({
      id: `source-${source.id}`,
      name: source.name,
      category: "Foydalanilgan manba" as const,
      kind: "source" as const,
    })),
    ...uploadedFiles.map((name) => ({
      id: `file-${name}`,
      name,
      category: "Yuklangan fayl" as const,
      kind: "upload" as const,
    })),
  ];
  const rowCount = Math.ceil(graphNodes.length / 2);
  const sceneHeight = Math.max(420, rowCount * 92 + 110);
  const positions = graphNodes.map((_, index) => {
    const row = Math.floor(index / 2);
    const side = index % 2 === 0 ? "left" : "right";
    const y = rowCount <= 1 ? 50 : 12 + row * (76 / (rowCount - 1));
    return { x: side === "left" ? 4 : 96, y, side };
  });
  const [rotation, setRotation] = useState({ x: 8, y: -10 });
  const [isDragging, setIsDragging] = useState(false);
  const drag = useRef({ active: false, x: 0, y: 0 });

  const rotateFromKeyboard = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const step = 8;
    if (event.key === "ArrowLeft") setRotation((current) => ({ ...current, y: current.y - step }));
    else if (event.key === "ArrowRight") setRotation((current) => ({ ...current, y: current.y + step }));
    else if (event.key === "ArrowUp") setRotation((current) => ({ ...current, x: Math.max(-55, current.x - step) }));
    else if (event.key === "ArrowDown") setRotation((current) => ({ ...current, x: Math.min(55, current.x + step) }));
    else return;
    event.preventDefault();
  };

  const startGlobeDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    drag.current = { active: true, x: event.clientX, y: event.clientY };
    setIsDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const moveGlobe = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.current.active) return;
    const deltaX = event.clientX - drag.current.x;
    const deltaY = event.clientY - drag.current.y;
    drag.current = { active: true, x: event.clientX, y: event.clientY };
    setRotation((current) => ({
      x: Math.max(-55, Math.min(55, current.x - deltaY * 0.45)),
      y: current.y + deltaX * 0.55,
    }));
  };

  const stopGlobeDrag = () => {
    drag.current.active = false;
    setIsDragging(false);
  };

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <button
        type="button"
        aria-label="AI miyasi oynasini yopish"
        onClick={onClose}
        className="absolute inset-0 bg-black/65 backdrop-blur-sm"
      />

      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="brain-panel-title"
        className="relative z-10 flex h-full w-full max-w-6xl flex-col border-l border-[#a7b4c4]/15 bg-[#0c121a] text-[#e8edf3] shadow-2xl"
      >
        <header className="flex shrink-0 items-center justify-between border-b border-gray-800/80 px-5 py-4 sm:px-7">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl border border-gray-700/70 bg-gray-800/60 text-sm font-semibold text-gray-200" aria-hidden="true">
              N
            </span>
            <div>
              <h2 id="brain-panel-title" className="text-base font-bold text-white sm:text-lg">Nexora AI miyasi</h2>
              <p className="mt-0.5 text-[11px] text-gray-400">Bitta chatdagi fayllar va foydalanilgan manbalar</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Yopish"
            className="grid h-10 w-10 place-items-center rounded-xl border border-gray-800 bg-gray-900/70 text-gray-300 transition-colors hover:border-gray-700 hover:text-white"
          >
            ✕
          </button>
        </header>

        <div className="brain-panel-grid min-h-0 flex-1">
          <main className="min-w-0 overflow-y-auto px-5 py-5 sm:px-7 sm:py-7">
            <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400">Manbalar grafigi</p>
                <p className="mt-1.5 max-w-xl text-xs leading-relaxed text-gray-400">
                  Faqat yuklangan fayllar va javoblarda foydalanilgan manbalar ko‘rsatiladi. Sharni sudrab aylantiring.
                </p>
              </div>
              <span className="rounded-full border border-gray-700/70 bg-gray-800/50 px-3 py-1 text-[10px] font-medium text-gray-300">3D</span>
            </div>

            <div className="brain-scene" style={{ minHeight: `${sceneHeight}px` }} role="group" aria-label={`Yagona chatdagi ${sources.length} ta foydalanilgan manba va ${uploadedFiles.length} ta yuklangan fayl grafigi`}>
              <svg className="brain-network" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                {graphNodes.map((node, index) => {
                  const { x, y } = positions[index];
                  return <path key={`connection-${node.id}`} className="brain-network-path" d={connectionPath(x, y)} />;
                })}
              </svg>
              <div className="brain-orb-wrap">
                <div
                  className={`brain-globe${isDragging ? " is-dragging" : ""}`}
                  role="application"
                  aria-label="3D shar. Sichqoncha yoki barmoq bilan sudrab, klaviaturadagi strelkalar orqali aylantiring."
                  tabIndex={0}
                  onPointerDown={startGlobeDrag}
                  onPointerMove={moveGlobe}
                  onPointerUp={stopGlobeDrag}
                  onPointerCancel={stopGlobeDrag}
                  onKeyDown={rotateFromKeyboard}
                >
                  <div className="brain-globe-surface" style={{ transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)` }}>
                    <span className="brain-globe-latitude" />
                    <span className="brain-globe-equator" />
                    <span className="brain-globe-longitude" />
                    <span className="brain-globe-meridian" />
                  </div>
                  <span className="brain-globe-highlight" />
                </div>
              </div>
              {graphNodes.map((node, index) => (
                <div
                  key={node.id}
                  className={`brain-node brain-node-${node.kind} brain-node-${positions[index].side}`}
                  style={{ left: `${positions[index].x}%`, top: `${positions[index].y}%` }}
                >
                  <span className="brain-node-dot" aria-hidden="true" />
                  <span className="min-w-0">
                    <small>{node.category}</small>
                    <strong title={node.name}>{node.name}</strong>
                  </span>
                </div>
              ))}
              <p className="brain-globe-hint">Sharni sudrab aylantiring</p>
            </div>
          </main>

          <aside className="brain-sources-pane overflow-y-auto border-l border-gray-800/90 px-5 py-5 sm:px-6 sm:py-7">
            <section aria-labelledby="brain-sources-title">
              <div className="flex items-center justify-between gap-3">
                <h3 id="brain-sources-title" className="text-xs font-bold text-white">Foydalanilgan manbalar</h3>
                <span className="rounded-full bg-gray-800 px-2 py-1 text-[10px] font-semibold text-gray-300">{sources.length}</span>
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-gray-500">Javoblarda foydalanilgan hujjatlar.</p>
              <ul className="mt-3 space-y-2">
                {sources.map((source) => (
                  <li key={source.id} className="brain-source-item">
                    <span className="brain-file-icon brain-file-source" aria-hidden="true">↗</span>
                    <span className="min-w-0 flex-1">
                      <strong title={source.name}>{source.name}</strong>
                      <small>{source.detail || "AI javobida ishlatilgan manba"}</small>
                    </span>
                  </li>
                ))}
              </ul>
              {sources.length === 0 && (
                <p className="brain-empty-state">Hozircha foydalanilgan manba yo‘q.</p>
              )}
            </section>

            <section className="mt-7 border-t border-gray-800/90 pt-5" aria-labelledby="brain-files-title">
              <div className="flex items-center justify-between gap-3">
                <h3 id="brain-files-title" className="text-xs font-bold text-white">Yuklangan fayllar</h3>
                <span className="rounded-full bg-gray-800 px-2 py-1 text-[10px] font-semibold text-gray-300">{uploadedFiles.length}</span>
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-gray-500">Bitta chatda saqlanadigan fayllar.</p>
              <ul className="mt-3 space-y-2">
                {uploadedFiles.map((file) => (
                  <li key={file} className="brain-source-item">
                    <span className="brain-file-icon brain-file-upload" aria-hidden="true">FILE</span>
                    <span className="min-w-0 flex-1">
                      <strong title={file}>{file}</strong>
                      <small>Yuklangan fayl</small>
                    </span>
                  </li>
                ))}
              </ul>
              {uploadedFiles.length === 0 && (
                <p className="brain-empty-state">Hali fayl yuklanmagan.</p>
              )}
            </section>
          </aside>
        </div>
      </section>
    </div>
  );
}
