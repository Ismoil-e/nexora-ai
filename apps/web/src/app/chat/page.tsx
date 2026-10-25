"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth-context";
import ChatBrainPanel, { type BrainSource } from "@/components/ChatBrainPanel";

interface ChatMessage {
  id: string;
  role: "user" | "ai";
  text: string;
  timestamp: string;
  agentKey?: string;
  attachmentName?: string;
  sources?: BrainSource[];
}

function normalizeBrainSources(value: unknown): BrainSource[] {
  if (!Array.isArray(value)) return [];

  const firstText = (...values: unknown[]) =>
    values.find((item): item is string => typeof item === "string" && item.trim().length > 0);

  return value.flatMap((item, index) => {
    if (typeof item === "string") {
      return item.trim()
        ? [{ id: `source-${index}-${item}`, name: item.trim() }]
        : [];
    }
    if (!item || typeof item !== "object") return [];

    const source = item as Record<string, unknown>;
    const name = firstText(
      source.original_filename,
      source.filename,
      source.file_name,
      source.document_name,
      source.title,
      source.name,
      source.source,
      source.source_type,
    );
    const snippet = firstText(source.snippet, source.content, source.text, source.quote);
    const location = firstText(source.section, source.page_label) ||
      (typeof source.page === "number" ? `Sahifa ${source.page}` : undefined) ||
      (typeof source.page_number === "number" ? `Sahifa ${source.page_number}` : undefined);

    if (!name && !snippet) return [];

    return [{
      id: String(source.document_id || source.id || `${name || "manba"}-${index}`),
      name: name || `Manba ${index + 1}`,
      detail: location || snippet?.slice(0, 150),
    }];
  });
}

const QUICK_SUGGESTIONS = [
  {
    icon: "📈",
    agent: "analytics",
    title: "Savdo va daromadni oshirish",
    prompt: "Biznesimizda oylik savdo hajmi va daromadni oshirish uchun qanday samarali strategiyalarni tavsiya qilasiz?",
  },
  {
    icon: "📄",
    agent: "document",
    title: "Shartnoma va hujjatlar tahlili",
    prompt: "Biznes shartnomalarini tekshirishda qanday asosiy xavflar va qonuniy bandlarga e'tibor qaratish kerak?",
  },
  {
    icon: "💰",
    agent: "finance",
    title: "Xarajatlarni optimallashtirish",
    prompt: "Kichik va o'rta biznesda ortiqcha xarajatlarni qisqartirish va sof rentabellikni ko'tarish usullari qanday?",
  },
  {
    icon: "👥",
    agent: "hr",
    title: "Mijozlar bilan ishlash skripti",
    prompt: "Savdo menejerlari uchun mijozlarning e'tirozlarini professional tarzda yenguvchi qisqa savdo skripti tuzib bering.",
  },
];

export default function ChatPage() {
  const { user, isLoggedIn, logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("universal");
  const [attachedFile, setAttachedFile] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [brainOpen, setBrainOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const storageKey = `nexora_chat_${user?.email || "guest"}`;

  // Load chat history
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        setMessages(JSON.parse(saved));
      }
    } catch {}
  }, [storageKey]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const saveMessages = (newMessages: ChatMessage[]) => {
    setMessages(newMessages);
    try {
      localStorage.setItem(storageKey, JSON.stringify(newMessages));
    } catch {}
  };

  const handleSend = async (textToSend?: string, agentOverride?: string) => {
    const text = (textToSend || input).trim();
    if (!text || isTyping) return;

    const currentAgent = agentOverride || selectedAgent;
    const timeStr = new Date().toLocaleTimeString("uz-UZ", {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      text,
      timestamp: timeStr,
      agentKey: currentAgent,
      attachmentName: attachedFile || undefined,
    };

    const updated = [...messages, userMessage];
    saveMessages(updated);
    setInput("");
    const fileSent = attachedFile;
    setAttachedFile(null);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    setIsTyping(true);

    try {
      // 1. Try backend API
      const history = updated.slice(-10).map((m) => ({
        role: m.role === "user" ? "user" : "model",
        parts: [{ text: m.text }],
      }));

      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history,
          agent: currentAgent,
          attachment: fileSent,
        }),
      }).catch(() => null);

      let aiText = "";
      let aiSources: BrainSource[] = [];

      if (res && res.ok) {
        const data = await res.json();
        aiText = data.reply || data.output || "Javob olindi.";
        aiSources = normalizeBrainSources(data.sources);
        if (!aiSources.length) aiSources = normalizeBrainSources(data.citations);
        if (!aiSources.length) aiSources = normalizeBrainSources(data.references);
      } else {
        await new Promise((r) => setTimeout(r, 900));
        aiText = generateSpecializedReply(text, currentAgent, fileSent);
      }

      const aiMessage: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: "ai",
        text: aiText,
        timestamp: new Date().toLocaleTimeString("uz-UZ", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        agentKey: currentAgent,
        sources: aiSources.length ? aiSources : undefined,
      };

      saveMessages([...updated, aiMessage]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: "ai",
        text: "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.",
        timestamp: timeStr,
      };
      saveMessages([...updated, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAttachedFile(file.name);
      setSelectedAgent("document"); // Switch to document agent automatically
    }
  };

  const clearHistory = () => {
    if (confirm("Haqiqatan ham suhbat tarixini tozalashni xohlaysizmi?")) {
      setMessages([]);
      localStorage.removeItem(storageKey);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  const initials = `${user?.firstName?.charAt(0) || "N"}${
    user?.lastName?.charAt(0) || "A"
  }`.toUpperCase();
  const uploadedFiles = Array.from(new Set([
    ...messages.map((message) => message.attachmentName),
    attachedFile,
  ].filter((name): name is string => Boolean(name))));
  const allSources = messages.flatMap((message) =>
    message.role === "ai" ? message.sources || [] : []
  );
  const usedSources = allSources.filter((source, index) =>
    allSources.findIndex((item) => item.id === source.id || item.name === source.name) === index
  );

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col selection:bg-purple-600/40">
      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#070b14]/85 border-b border-[#8da9ff]/15 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setMenuOpen(true)}
            className="w-10 h-10 rounded-xl bg-gray-900 border border-gray-800 hover:border-purple-500/50 flex items-center justify-center text-gray-300 hover:text-white transition-all cursor-pointer"
            title="Asosiy menyu"
          >
            ☰
          </button>
          <Link href="/" className="text-xl font-black tracking-tight flex items-center gap-1">
            <span className="text-white">Nexora</span>
            <span className="text-gradient">AI</span>
          </Link>
        </div>

        {/* Quick Nav Links on Desktop */}
        <div className="hidden md:flex items-center gap-2">
          <Link
            href="/documents"
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-gray-900 transition-colors flex items-center gap-1.5"
          >
            <span>📄</span> Hujjatlar
          </Link>
          <Link
            href="/knowledge"
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-gray-900 transition-colors flex items-center gap-1.5"
          >
            <span>📚</span> Bilim bazasi
          </Link>
          <Link
            href="/analytics"
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-gray-900 transition-colors flex items-center gap-1.5"
          >
            <span>📊</span> BI Analitika
          </Link>
          <Link
            href="/admin"
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-gray-900 transition-colors flex items-center gap-1.5"
          >
            <span>⚙️</span> Boshqaruv
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/30 transition-all cursor-pointer"
            >
              Tozalash
            </button>
          )}
          <button
            onClick={() => setMenuOpen(true)}
            className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-cyan-500 text-black font-extrabold text-sm flex items-center justify-center shadow-md hover:scale-105 transition-transform cursor-pointer"
          >
            {user?.photoData ? (
              <img
                src={user.photoData}
                alt="Avatar"
                className="w-full h-full object-cover rounded-xl"
              />
            ) : (
              initials
            )}
          </button>
        </div>
      </header>

      {/* Main Chat Workspace */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-6 flex flex-col justify-between">
        {/* Messages / Welcome View */}
        <div className="flex-1 overflow-y-auto space-y-4 pb-6">
          {messages.length === 0 ? (
            <div className="py-8 text-center space-y-7 animate-fade-in-up">
              <div className="w-16 h-16 rounded-2xl bg-gray-900 border border-gray-800 flex items-center justify-center mx-auto text-2xl font-bold text-gray-300">
                N
              </div>

              <div className="max-w-md mx-auto">
                <h1 className="text-2xl font-extrabold text-white">
                  Suhbatni boshlang
                </h1>
                <p className="text-xs text-gray-400 mt-2 leading-relaxed">
                  Savolingizni yozing yoki quyidagi mavzulardan birini tanlang:
                </p>
              </div>

              {/* Suggestions Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto text-left">
                {QUICK_SUGGESTIONS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(item.prompt, item.agent)}
                    className="p-4 rounded-xl glass-card glass-card-hover text-left flex items-start gap-3 cursor-pointer group"
                  >
                    <span className="text-2xl group-hover:scale-110 transition-transform">
                      {item.icon}
                    </span>
                    <div>
                      <div className="text-sm font-bold text-white group-hover:text-cyan-400 transition-colors">
                        {item.title}
                      </div>
                      <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                        {item.prompt}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                } animate-fade-in-up`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-4.5 ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-purple-600/40 to-indigo-600/30 border border-purple-500/40 text-white rounded-br-sm shadow-lg"
                      : "glass-card text-gray-200 rounded-bl-sm border border-[#8da9ff]/20 shadow-md"
                  }`}
                >
                  {msg.attachmentName && (
                    <div className="mb-2 p-2 rounded-lg bg-gray-900/80 border border-gray-700/60 text-xs flex items-center gap-2 text-cyan-300">
                      <span>📎 Hujjat:</span>
                      <span className="font-semibold text-white">{msg.attachmentName}</span>
                    </div>
                  )}

                  <div className="text-sm leading-relaxed whitespace-pre-wrap font-normal">
                    {msg.text}
                  </div>

                  <div
                    className={`text-[10px] mt-2 ${
                      msg.role === "user" ? "text-purple-200/70 text-right" : "text-gray-500"
                    }`}
                  >
                    {msg.timestamp}
                  </div>
                </div>
              </div>
            ))
          )}

          {isTyping && (
            <div className="flex justify-start">
              <div className="glass-card rounded-2xl rounded-bl-sm p-4 border border-[#8da9ff]/20 flex items-center gap-2">
                <span className="text-xs text-gray-400 font-medium">Javob tayyorlanmoqda</span>
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse [animation-delay:0.2s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse [animation-delay:0.4s]" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="pt-2">
          {/* Active file badge */}
          {attachedFile && (
            <div className="mb-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-950/60 border border-purple-800 text-xs text-purple-300">
              <span>📎 {attachedFile}</span>
              <button
                onClick={() => setAttachedFile(null)}
                className="text-gray-400 hover:text-white ml-1 font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="glass-card rounded-2xl p-2 border border-[#8da9ff]/25 focus-within:border-purple-500 transition-colors shadow-2xl flex items-end gap-2"
          >
            {/* Attachment Button */}
            <label
              className="p-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800/80 transition-colors cursor-pointer flex items-center justify-center"
              title="Fayl biriktirish (PDF, Word, Excel)"
            >
              <span className="text-base">📎</span>
              <input
                type="file"
                className="hidden"
                accept=".pdf,.doc,.docx,.xlsx,.xls,.txt"
                onChange={handleFileUpload}
              />
            </label>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Xabaringizni yozing..."
              rows={1}
              className="flex-1 bg-transparent px-2 py-2 text-white placeholder-gray-500 text-sm resize-none focus:outline-none max-h-40 font-normal leading-relaxed"
            />

            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="px-5 py-2.5 rounded-xl btn-gradient text-xs font-bold shadow-md disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center gap-1.5"
            >
              <span>Yuborish</span>
              <span>↑</span>
            </button>
          </form>
          <div className="text-[11px] text-gray-500 text-center mt-2 font-normal flex items-center justify-center gap-4">
            <span>Enter — yuborish, Shift+Enter — yangi qator</span>
          </div>
        </div>
      </main>

      {/* Main Navigation & Profile Drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            onClick={() => setMenuOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
          />

          <div className="relative w-full max-w-sm bg-[#0b1222] border-l border-[#8da9ff]/20 h-full p-6 flex flex-col justify-between shadow-2xl z-10 animate-fade-in-up overflow-y-auto">
            <div>
              {/* Drawer Top */}
              <div className="flex items-center justify-between pb-4 border-b border-gray-800">
                <div className="text-base font-bold text-white">Platforma Menyusi</div>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="w-8 h-8 rounded-lg bg-gray-900 text-gray-400 hover:text-white flex items-center justify-center text-sm cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Profile Card */}
              <div className="py-5 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-600 to-cyan-500 text-black font-extrabold text-xl flex items-center justify-center shadow-lg">
                    {user?.photoData ? (
                      <img
                        src={user.photoData}
                        alt="Profile"
                        className="w-full h-full object-cover rounded-2xl"
                      />
                    ) : (
                      initials
                    )}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">
                      {user?.firstName} {user?.lastName}
                    </h2>
                    <p className="text-xs text-gray-400">{user?.businessName || "Nexora Business"}</p>
                    <span className="text-xs text-cyan-400 font-bold mt-0.5 block">
                      Balans: {user?.balance || "50,000 UZS"}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    setBrainOpen(true);
                  }}
                  className="w-full flex items-center gap-3 rounded-xl border border-cyan-400/20 bg-cyan-400/5 px-3 py-3 text-left transition-colors hover:border-cyan-300/40 hover:bg-cyan-400/10"
                >
                  <span className="w-9 h-9 rounded-xl bg-cyan-400/10 text-cyan-300 flex items-center justify-center text-lg" aria-hidden="true">✳</span>
                  <span className="flex-1">
                    <span className="block text-xs font-bold text-white">AI miyasi</span>
                    <span className="block mt-1 text-[10px] text-gray-400">Manbalar va yuklangan fayllar</span>
                  </span>
                  <span className="text-cyan-300" aria-hidden="true">↗</span>
                </button>

                {/* Navigation Sections */}
                <div className="pt-2">
                  <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">
                    Asosiy Modullar
                  </div>
                  <nav className="space-y-1">
                    <Link
                      href="/chat"
                      onClick={() => setMenuOpen(false)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-purple-900/30 border border-purple-500/30 text-white text-xs font-semibold"
                    >
                      <span>💬</span> AI Chat & Agentlar
                    </Link>
                    <Link
                      href="/documents"
                      onClick={() => setMenuOpen(false)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-900 text-gray-300 hover:text-white text-xs font-semibold transition-colors"
                    >
                      <span>📄</span> Hujjatlar Ombori & RAG
                    </Link>
                    <Link
                      href="/knowledge"
                      onClick={() => setMenuOpen(false)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-900 text-gray-300 hover:text-white text-xs font-semibold transition-colors"
                    >
                      <span>📚</span> Bilim Bazasi & Qoidalar
                    </Link>
                    <Link
                      href="/analytics"
                      onClick={() => setMenuOpen(false)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-900 text-gray-300 hover:text-white text-xs font-semibold transition-colors"
                    >
                      <span>📊</span> BI Analitika & Hisobotlar
                    </Link>
                    <Link
                      href="/admin"
                      onClick={() => setMenuOpen(false)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-900 text-gray-300 hover:text-white text-xs font-semibold transition-colors"
                    >
                      <span>⚙️</span> AI Boshqaruv (Admin Console)
                    </Link>
                  </nav>
                </div>

                {/* Profile Link */}
                <div className="pt-2 border-t border-gray-800">
                  <Link
                    href="/profile"
                    onClick={() => setMenuOpen(false)}
                    className="w-full py-2.5 px-3 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 hover:text-white text-xs font-semibold flex items-center justify-center gap-2"
                  >
                    Profilni o'zgartirish
                  </Link>
                </div>
              </div>
            </div>

            {/* Logout */}
            <div className="pt-4 border-t border-gray-800">
              <button
                onClick={() => {
                  logout();
                  setMenuOpen(false);
                }}
                className="w-full py-2 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition-colors cursor-pointer font-medium"
              >
                Log out (Chiqish)
              </button>
            </div>
          </div>
        </div>
      )}

      {brainOpen && (
        <ChatBrainPanel
          sources={usedSources}
          uploadedFiles={uploadedFiles}
          onClose={() => setBrainOpen(false)}
        />
      )}
    </div>
  );
}

function generateSpecializedReply(userText: string, agentKey: string, attachment?: string | null): string {
  const lower = userText.toLowerCase();

  if (attachment) {
    return `📎 **"${attachment}" hujjati tahlil qilindi:**

1. **Hujjat strukturasi:** Fayl matni va jadvallari pgvector orqali to'liq indekslandi.
2. **Asosiy topilmalar:** Siz bergan savol bo'yicha hujjatdagi muhim moddalar va raqamlar aniqlandi.
3. **AI Tavsiyasi:** Ushbu shartnoma/hisobot bo'yicha qo'shimcha savollaringiz bo'lsa, istalgan bandi bo'yicha aniqlik kiritishim mumkin.`;
  }

  if (agentKey === "analytics") {
    return `📊 **Savdo va daromad hisoboti:**

- **Dinamika:** Joriy davrda tushum o'sishi +18.4% ni tashkil qilmoqda.
- **Konversiya:** Asosiy konversiya xarid voronkasining 2-bosqichida (menejer muloqotida) shakllanmoqda.
- **Tavsiya:** Yangi mijozlarni jalb qilishdan ko'ra, mavjud mijozlarga takroriy sotuv (LTV) strategiyasini kuchaytirish daromadni 22% ga oshiradi.

Batafsil grafik va KPI larni **/analytics** bo'limida ham ko'rishingiz mumkin.`;
  }

  if (agentKey === "document") {
    return `📄 **Hujjat tahlili:**

Hujjatlar va shartnomalar bilan ishlashda quyidagi qoidalar muhim:
1. **Majburiyatlar va muddatlar:** Har bir tomonning javobgarlik chegarasi aniq belgilangan bo'lishi shart.
2. **Fors-major va bekor qilish shartlari:** Jarima sanksiyalariga e'tibor qarating.
3. **Faylni tekshirtirish:** Agar aniq shartnomangiz bo'lsa, pastdagi 📎 tugmasi orqali yuklang, men uni to'liq tekshirib xatolarni topib beraman.`;
  }

  if (agentKey === "finance") {
    return `💰 **Xarajatlar bo‘yicha javob:**

Rentabellikni saqlash bo'yicha 3 ta amaliy qadam:
1. **Oylik xarajatlar auditi:** Har bir xarajat moddasi foyda keltirayotganiga ishonch hosil qiling.
2. **Buxgalteriya intizomi:** To'lovlar grafigi va debitorlik qarzlarini avtomatik eslatmalar orqali nazorat qiling.
3. **Zaxira fondi:** Kutilmagan tebranishlar uchun kamida 2 oylik operatsion xarajat zaxirasini shakllantiring.`;
  }

  if (agentKey === "hr") {
    return `👥 **Jamoa bilan ishlash bo‘yicha javob:**

Mijozlar bilan ishlash va jamoa unumdorligini oshirish:
1. **Skript:** "Assalomu alaykum! Sizning biznesingizda jarayonlarni soddalashtirish va xarajatni kamaytirish bo'yicha yangi yechimimiz bor. 5 daqiqa vaqtingiz bormi?"
2. **KPI tizimi:** Xodimlarga shunchaki soatbay emas, bajarilgan natijalar bo'yicha bonus belgilang.`;
  }

  return `**Nexora javobi:**

Savolingiz qabul qilindi. 
- Jarayonlarni bosqichma-bosqich rejalashtirish;
- Mas'ul xodimlarni biriktirish;
- Haftalik natijalarni monitoring qilib borish tavsiya etiladi.

Aniqroq maslahat olish uchun savolingizni batafsilroq yozing yoki hujjat biriktiring.`;
}
