"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { useState } from "react";

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
  const { user, logout } = useAuth();
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
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top Bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="text-gray-400 hover:text-white transition-colors">
            ← Orqaga
          </Link>
          <div className="w-px h-5 bg-gray-700" />
          <span className="text-lg">📚</span>
          <span className="text-white font-medium">Bilim bazalari</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{user?.name}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-red-400 cursor-pointer"
          >
            Chiqish
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto w-full p-8 flex-1">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Bilim bazalari (Knowledge Base)</h1>
            <p className="text-gray-400 text-sm mt-1">
              RAG va semantik vektor qidiruvi uchun tuzilgan bilimlar to'plami
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer flex items-center gap-2"
          >
            <span>+ Yangi baza yaratish</span>
          </button>
        </div>

        {/* Semantic Search Bar */}
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Barcha bilim bazalari bo'yicha semantik AI qidiruv..."
              className="flex-1 bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 transition-colors"
            />
            <button
              type="submit"
              disabled={searching}
              className="px-6 py-3 bg-gray-800 hover:bg-gray-700 text-blue-400 border border-gray-700 rounded-xl text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              {searching ? "Qidirilmoqda..." : "🔍 Qidirish"}
            </button>
          </div>
        </form>

        {/* Search Results */}
        {searchResults && (
          <div className="mb-8 bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-300">
                Semantik qidiruv natijalari:
              </h2>
              <button
                onClick={() => setSearchResults(null)}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                Yopish ✕
              </button>
            </div>
            <div className="space-y-3">
              {searchResults.map((res) => (
                <div
                  key={res.id}
                  className="p-4 bg-gray-800/40 border border-gray-700/50 rounded-xl"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-blue-400">{res.kb}</span>
                    <span className="text-xs text-green-400 bg-green-950/50 px-2 py-0.5 rounded">
                      {res.score}
                    </span>
                  </div>
                  <p className="text-sm text-gray-300">{res.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Knowledge Bases Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {knowledgeBases.map((kb) => (
            <div
              key={kb.id}
              className="p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-colors flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="w-12 h-12 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center text-2xl">
                    {kb.icon}
                  </div>
                  <span className="text-xs text-gray-500">Yangilandi: {kb.updatedAt}</span>
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{kb.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed mb-4">{kb.description}</p>
              </div>

              <div className="pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500">
                <span>{kb.sourcesCount} ta manba</span>
                <span>{kb.vectorsCount.toLocaleString()} ta vektor embedding</span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-md w-full p-6">
              <h2 className="text-lg font-bold text-white mb-4">Yangi bilim bazasi yaratish</h2>
              <form onSubmit={handleAddKB} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">
                    Baza nomi
                  </label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Masalan: Maxsulotlar qollanmasi"
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">
                    Tavsifi
                  </label>
                  <textarea
                    rows={3}
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Ushbu baza nimaga mo'ljallangan..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-sm cursor-pointer"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium cursor-pointer"
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
