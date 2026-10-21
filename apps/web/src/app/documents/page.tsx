"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

interface DocumentItem {
  id: string;
  name: string;
  size: string;
  type: string;
  uploadedAt: string;
  status: "indexed" | "processing" | "ready";
  chunksCount: number;
}

const INITIAL_DOCS: DocumentItem[] = [
  {
    id: "doc-1",
    name: "Kompaniya_Nizomi_2026.pdf",
    size: "2.4 MB",
    type: "PDF",
    uploadedAt: "2026-10-15 14:20",
    status: "indexed",
    chunksCount: 42,
  },
  {
    id: "doc-2",
    name: "Moliyaviy_Hisobot_Q3.xlsx",
    size: "1.1 MB",
    type: "EXCEL",
    uploadedAt: "2026-10-18 09:45",
    status: "indexed",
    chunksCount: 18,
  },
  {
    id: "doc-3",
    name: "Savdo_Skripti_va_Shartnomalar.docx",
    size: "850 KB",
    type: "WORD",
    uploadedAt: "2026-10-20 16:10",
    status: "indexed",
    chunksCount: 29,
  },
];

export default function DocumentsPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>(INITIAL_DOCS);
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    setIsUploading(true);

    setTimeout(() => {
      const newDoc: DocumentItem = {
        id: `doc-${Date.now()}`,
        name: file.name,
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        type: file.name.split(".").pop()?.toUpperCase() || "FILE",
        uploadedAt: new Date().toISOString().slice(0, 16).replace("T", " "),
        status: "indexed",
        chunksCount: Math.floor(Math.random() * 30) + 12,
      };
      setDocuments((prev) => [newDoc, ...prev]);
      setIsUploading(false);
    }, 1200);
  };

  const handleDelete = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (selectedDoc?.id === id) setSelectedDoc(null);
  };

  const filteredDocs = documents.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col selection:bg-purple-600/40">
      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#070b14]/85 border-b border-[#8da9ff]/15 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="text-xs font-semibold text-gray-400 hover:text-white transition-colors flex items-center gap-1.5"
          >
            <span>←</span>
            <span>Chatga qaytish</span>
          </Link>
          <div className="w-px h-4 bg-gray-800" />
          <div className="text-lg font-black tracking-tight flex items-center gap-1">
            <span className="text-white">Nexora</span>
            <span className="text-gradient">AI</span>
            <span className="ml-2 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-cyan-900/40 text-cyan-400 border border-cyan-800/40">
              Hujjatlar Ombori
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/chat"
            className="px-4 py-2 rounded-xl btn-gradient text-xs font-bold shadow-md"
          >
            AI bilan tahlil qilish 💬
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto w-full p-6 sm:p-8 flex-1">
        {/* Title */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-black text-white">Hujjatlar & Fayl Razvedkasi</h1>
            <p className="text-xs text-gray-400 mt-1">
              PDF, Word, Excel shartnoma va hisobotlarni yuklang — AI ularni avtomatik o'qiydi va tahlil qiladi
            </p>
          </div>

          <label className="px-5 py-2.5 rounded-xl btn-gradient text-xs font-bold shadow-lg transition-all cursor-pointer flex items-center gap-2">
            <span>+ Yangi hujjat yuklash</span>
            <input
              type="file"
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.doc,.docx,.xlsx,.xls,.txt"
            />
          </label>
        </div>

        {/* Upload indicator */}
        {isUploading && (
          <div className="mb-6 p-4 rounded-2xl glass-card border-cyan-500/30 flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-cyan-300 font-medium">
              Hujjat matni ajratilmoqda va pgvector bilim bazasiga embedding qilinmoqda...
            </span>
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="glass-card rounded-2xl p-4 border border-[#8da9ff]/15">
            <div className="text-xs text-gray-400 font-medium">Jami hujjatlar</div>
            <div className="text-2xl font-black text-white mt-1">{documents.length} ta</div>
          </div>
          <div className="glass-card rounded-2xl p-4 border border-[#8da9ff]/15">
            <div className="text-xs text-gray-400 font-medium">Indekslangan AI qismlari (Chunks)</div>
            <div className="text-2xl font-black text-cyan-400 mt-1">
              {documents.reduce((acc, d) => acc + d.chunksCount, 0)} ta
            </div>
          </div>
          <div className="glass-card rounded-2xl p-4 border border-[#8da9ff]/15">
            <div className="text-xs text-gray-400 font-medium">Qidiruv aniqligi (Hybrid RAG)</div>
            <div className="text-2xl font-black text-purple-400 mt-1">98.4%</div>
          </div>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Hujjat nomini qidirish..."
            className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-purple-500 transition-colors"
          />
        </div>

        {/* Documents Table */}
        <div className="glass-card rounded-2xl border border-[#8da9ff]/15 overflow-hidden">
          {filteredDocs.length === 0 ? (
            <div className="p-12 text-center text-gray-500 text-xs">
              Hujjatlar topilmadi. Yuqoridagi tugma orqali yangi hujjat yuklang!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-gray-800 text-[11px] text-gray-400 uppercase tracking-wider bg-gray-900/40">
                    <th className="px-6 py-3.5">Fayl nomi</th>
                    <th className="px-6 py-3.5">Hajmi</th>
                    <th className="px-6 py-3.5">Yuklangan sana</th>
                    <th className="px-6 py-3.5">AI Tahlil holati</th>
                    <th className="px-6 py-3.5">Amallar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 text-xs">
                  {filteredDocs.map((doc) => (
                    <tr
                      key={doc.id}
                      className="hover:bg-gray-800/30 transition-colors"
                    >
                      <td className="px-6 py-4 flex items-center gap-3">
                        <span className="text-xl">
                          {doc.type === "PDF"
                            ? "📕"
                            : doc.type === "EXCEL" || doc.type === "XLSX"
                            ? "📊"
                            : "📘"}
                        </span>
                        <div>
                          <div className="font-bold text-white">{doc.name}</div>
                          <div className="text-[11px] text-gray-400">
                            {doc.chunksCount} ta semantik vektor
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-400">{doc.size}</td>
                      <td className="px-6 py-4 text-gray-400">{doc.uploadedAt}</td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-green-900/30 text-green-400 border border-green-800/40 flex items-center gap-1.5 w-fit">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                          Tayyor (RAG faol)
                        </span>
                      </td>
                      <td className="px-6 py-4 flex items-center gap-3">
                        <Link
                          href="/chat"
                          className="text-cyan-400 hover:text-cyan-300 font-semibold"
                        >
                          Chatda so'rash →
                        </Link>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="text-red-400 hover:text-red-300 transition-colors cursor-pointer"
                        >
                          O'chirish
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
