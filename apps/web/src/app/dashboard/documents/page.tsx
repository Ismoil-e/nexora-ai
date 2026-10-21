"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { useState } from "react";

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
    type: "Excel",
    uploadedAt: "2026-10-18 09:45",
    status: "indexed",
    chunksCount: 18,
  },
  {
    id: "doc-3",
    name: "Texnik_Qollanma_API.docx",
    size: "850 KB",
    type: "Word",
    uploadedAt: "2026-10-20 16:10",
    status: "ready",
    chunksCount: 29,
  },
];

export default function DocumentsPage() {
  const { user, logout } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>(INITIAL_DOCS);
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

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
        chunksCount: Math.floor(Math.random() * 30) + 10,
      };
      setDocuments((prev) => [newDoc, ...prev]);
      setIsUploading(false);
    }, 1200);
  };

  const handleDelete = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  const filteredDocs = documents.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top Bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="text-gray-400 hover:text-white transition-colors">
            ← Orqaga
          </Link>
          <div className="w-px h-5 bg-gray-700" />
          <span className="text-lg">📄</span>
          <span className="text-white font-medium">Hujjatlarim</span>
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
            <h1 className="text-2xl font-bold text-white">Hujjatlar ombori</h1>
            <p className="text-gray-400 text-sm mt-1">
              AI tahlili va qidiruv uchun hujjatlarni yuklang va boshqaring
            </p>
          </div>
          <label className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer flex items-center gap-2">
            <span>+ Hujjat yuklash</span>
            <input
              type="file"
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.doc,.docx,.xlsx,.xls,.txt"
            />
          </label>
        </div>

        {/* Upload status */}
        {isUploading && (
          <div className="mb-6 p-4 bg-blue-950/40 border border-blue-800 rounded-xl flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-blue-300">
              Hujjat yuklanmoqda va AI tomonidan indekslanmoqda...
            </span>
          </div>
        )}

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Hujjat nomini qidirish..."
            className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        {/* Document List */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {filteredDocs.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              Hujjatlar topilmadi. Yangi hujjat yuklang!
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                  <th className="px-6 py-4">Nomi</th>
                  <th className="px-6 py-4">Hajmi</th>
                  <th className="px-6 py-4">Yuklangan vaqt</th>
                  <th className="px-6 py-4">AI Holati</th>
                  <th className="px-6 py-4">Amallar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-6 py-4 flex items-center gap-3">
                      <span className="text-xl">
                        {doc.type === "PDF"
                          ? "📕"
                          : doc.type === "EXCEL" || doc.type === "XLSX"
                          ? "📊"
                          : "📘"}
                      </span>
                      <div>
                        <div className="font-medium text-white text-sm">{doc.name}</div>
                        <div className="text-xs text-gray-500">{doc.chunksCount} ta AI qismlari</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-400">{doc.size}</td>
                    <td className="px-6 py-4 text-sm text-gray-400">{doc.uploadedAt}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                          doc.status === "indexed"
                            ? "bg-green-900/40 text-green-400 border border-green-800/50"
                            : "bg-blue-900/40 text-blue-400 border border-blue-800/50"
                        }`}
                      >
                        {doc.status === "indexed" ? "✓ Indekslangan" : "Tayyor"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="text-xs text-red-400 hover:text-red-300 transition-colors cursor-pointer"
                      >
                        O'chirish
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
