"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

interface KnowledgeBase {
  id: string;
  title: string;
  description: string;
  sourcesCount: number;
  vectorsCount: number;
  updatedAt: string;
  icon: string;
}

const INITIAL_KBS: KnowledgeBase[] = [
  {
    id: "kb-1",
    title: "Kompaniya Qoidalari va Siyosati",
    description: "Ichki tartib-qoidalar, xodimlar huquq va majburiyatlari, xavfsizlik protokollari.",
    sourcesCount: 8,
    vectorsCount: 1420,
    updatedAt: "2026-10-19",
    icon: "🏢",
  },
  {
    id: "kb-2",
    title: "Mijozlarga Xizmat Ko'rsatish (Support FAQ)",
    description: "Ko'p beriladigan savollar, muammolar yechimi va qo'llab-quvvatlash skriptlari.",
    sourcesCount: 15,
    vectorsCount: 3200,
    updatedAt: "2026-10-21",
    icon: "🎧",
  },
  {
    id: "kb-3",
    title: "Mahsulotlar va Narxlar Katalogi",
    description: "Xizmatlar tavsifi, narxlar jadvali, chegirmalar va texnik parametrlar.",
    sourcesCount: 5,
    vectorsCount: 940,
    updatedAt: "2026-10-14",
    icon: "📦",
  },
];

export default function KnowledgePage() {
  const { user } = useAuth();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>(INITIAL_KBS);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearching(true);
    setTimeout(() => {
      setSearchResults([
        {
          id: 1,
          kb: "Kompaniya Qoidalari va Siyosati",
          snippet: `"${query}" bo'yicha topilgan kontekst: Xodimlar va kompaniya o'rtasidagi kelishuvlar hamda rasmiy qoidalar tizimi orqali avtomatik tahlil qilindi.`,
          score: "94% moslik",
        },
        {
          id: 2,
          kb: "Mijozlarga Xizmat Ko'rsatish",
          snippet: `Qidiruv natijasi: Mijozlar bilan ishlash bo'limi ushbu so'rov bo'yicha ko'rsatilgan choralarni ko'radi va tizimda qayd qiladi.`,
          score: "88% moslik",
        },
      ]);
      setSearching(false);
    }, 600);
  };

  const handleAddKB = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const newKb: KnowledgeBase = {
      id: `kb-${Date.now()}`,
      title: newTitle,
      description: newDesc || "Yangi bilim bazasi",
      sourcesCount: 0,
      vectorsCount: 0,
      updatedAt: new Date().toISOString().slice(0, 10),
      icon: "📚",
    };

    setKnowledgeBases((prev) => [newKb, ...prev]);
    setNewTitle("");
    setNewDesc("");
    setShowAddModal(false);
  };

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
            <span className="ml-2 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-900/40 text-purple-400 border border-purple-800/40">
              Bilim Bazalari
            </span>
          </div>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 rounded-xl btn-gradient text-xs font-bold shadow-md cursor-pointer"
        >
          + Yangi baza yaratish
        </button>
      </header>

      <div className="max-w-6xl mx-auto w-full p-6 sm:p-8 flex-1">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-2xl font-black text-white">Kompaniya Bilim Bazasi & RAG</h1>
          <p className="text-xs text-gray-400 mt-1">
            Biznesingizga oid qoidalar, qo'llanmalar va ma'lumotlar bitta aqlli qidiruv tizimida
          </p>
        </div>

        {/* Semantic Search Bar */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="glass-card rounded-2xl p-2 border border-[#8da9ff]/25 flex items-center gap-2 shadow-xl focus-within:border-cyan-500 transition-colors">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Barcha bilim bazalari bo'yicha semantik AI qidiruv..."
              className="flex-1 bg-transparent px-4 py-2 text-white placeholder-gray-500 text-xs focus:outline-none"
            />
            <button
              type="submit"
              disabled={searching}
              className="px-6 py-2.5 rounded-xl btn-gradient text-xs font-bold cursor-pointer disabled:opacity-50"
            >
              {searching ? "Qidirilmoqda..." : "🔍 Qidirish"}
            </button>
          </div>
        </form>

        {/* Search Results */}
        {searchResults && (
          <div className="mb-8 glass-card rounded-2xl p-6 border border-cyan-500/30">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold text-cyan-400 uppercase tracking-wider">
                Semantik qidiruv natijalari:
              </h2>
              <button
                onClick={() => setSearchResults(null)}
                className="text-xs text-gray-500 hover:text-white"
              >
                ✕ Yopish
              </button>
            </div>
            <div className="space-y-3">
              {searchResults.map((res) => (
                <div
                  key={res.id}
                  className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-white">{res.kb}</span>
                    <span className="text-[10px] text-green-400 font-semibold px-2 py-0.5 rounded bg-green-950/60 border border-green-800/40">
                      {res.score}
                    </span>
                  </div>
                  <p className="text-gray-300 leading-relaxed">{res.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Knowledge Bases Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {knowledgeBases.map((kb) => (
            <div
              key={kb.id}
              className="glass-card glass-card-hover rounded-2xl p-6 border border-[#8da9ff]/15 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-xl bg-purple-900/30 border border-purple-800/40 flex items-center justify-center text-2xl">
                    {kb.icon}
                  </div>
                  <span className="text-[10px] text-gray-500 font-medium">
                    {kb.updatedAt}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mb-2">{kb.title}</h3>
                <p className="text-xs text-gray-400 leading-relaxed mb-4">{kb.description}</p>
              </div>

              <div className="pt-4 border-t border-gray-800 flex items-center justify-between text-[11px] text-gray-500">
                <span>{kb.sourcesCount} ta manba</span>
                <span className="text-cyan-400 font-semibold">
                  {kb.vectorsCount.toLocaleString()} ta vektor
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="glass-card rounded-3xl p-6 border border-[#8da9ff]/30 max-w-md w-full shadow-2xl">
              <h2 className="text-lg font-bold text-white mb-2">Yangi bilim bazasi yaratish</h2>
              <p className="text-xs text-gray-400 mb-6">
                Kompaniyangiz yo'nalishi bo'yicha maxsus bilim manbalarini birlashtiring
              </p>
              <form onSubmit={handleAddKB} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">
                    Baza nomi
                  </label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Masalan: Maxsulotlar qollanmasi"
                    className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-2.5 text-white text-xs focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">
                    Tavsifi
                  </label>
                  <textarea
                    rows={3}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Ushbu baza nimaga mo'ljallangan..."
                    className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-2.5 text-white text-xs focus:outline-none focus:border-purple-500 resize-none"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 rounded-xl bg-gray-900 text-gray-400 text-xs font-semibold cursor-pointer"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl btn-gradient text-xs font-bold shadow-md cursor-pointer"
                  >
                    Yaratish
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
