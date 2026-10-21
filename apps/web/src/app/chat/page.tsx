"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth-context";

interface ChatMessage {
  id: string;
  role: "user" | "ai";
  text: string;
  timestamp: string;
}

const QUICK_SUGGESTIONS = [
  {
    icon: "📈",
    title: "Savdo va daromadni oshirish",
    prompt: "Biznesimizda oylik savdo hajmi va daromadni oshirish uchun qanday samarali strategiyalarni tavsiya qilasiz?",
  },
  {
    icon: "🤝",
    title: "Mijozlar bilan ishlash skripti",
    prompt: "Yangi mijozlar bilan muloqot qilish va e'tirozlarni yengish bo'yicha amaliy savdo skriptini tuzib bering.",
  },
  {
    icon: "💰",
    title: "Xarajatlarni optimallashtirish",
    prompt: "Kichik va o'rta biznesda ortiqcha xarajatlarni qisqartirish va rentabellikni ko'tarish usullari qanday?",
  },
  {
    icon: "🚀",
    title: "Marketing va reklama rejasi",
    prompt: "Kam byudjet bilan yangi mahsulotni bozorga olib chiqish va birinchi 100 ta mijozni jalb qilish rejasi.",
  },
];

export default function ChatPage() {
  const { user, isLoggedIn, logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const storageKey = `nexora_chat_${user?.email || "guest"}`;

  // Load chat history from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        setMessages(JSON.parse(saved));
      }
    } catch {}
  }, [storageKey]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const saveMessages = (newMessages: ChatMessage[]) => {
    setMessages(newMessages);
    try {
      localStorage.setItem(storageKey, JSON.stringify(newMessages));
    } catch {}
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || isTyping) return;

    const timeStr = new Date().toLocaleTimeString("uz-UZ", {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      text,
      timestamp: timeStr,
    };

    const updated = [...messages, userMessage];
    saveMessages(updated);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    setIsTyping(true);

    try {
      // 1. Backend API ga so'rov yuborishga harakat qilamiz
      const history = updated.slice(-10).map((m) => ({
        role: m.role === "user" ? "user" : "model",
        parts: [{ text: m.text }],
      }));

      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      }).catch(() => null);

      let aiText = "";

      if (res && res.ok) {
        const data = await res.json();
        aiText = data.reply || data.output || "Javob olindi.";
      } else {
        // Fallback or demo smart reply
        await new Promise((r) => setTimeout(r, 900));
        aiText = generateSmartReply(text);
      }

      const aiMessage: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: "ai",
        text: aiText,
        timestamp: new Date().toLocaleTimeString("uz-UZ", {
          hour: "2-digit",
          minute: "2-digit",
        }),
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

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col selection:bg-purple-600/40">
      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#070b14]/85 border-b border-[#8da9ff]/15 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setMenuOpen(true)}
            className="w-10 h-10 rounded-xl bg-gray-900 border border-gray-800 hover:border-purple-500/50 flex items-center justify-center text-gray-300 hover:text-white transition-all cursor-pointer"
            title="Profil menyusi"
          >
            ☰
          </button>
          <Link href="/" className="text-xl font-black tracking-tight flex items-center gap-1">
            <span className="text-white">Nexora</span>
            <span className="text-gradient">AI</span>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/30 transition-all cursor-pointer"
            >
              Tarixni tozalash
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
            <div className="py-12 text-center space-y-8 animate-fade-in-up">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600/30 to-cyan-500/30 border border-purple-500/30 flex items-center justify-center mx-auto text-3xl shadow-xl">
                💬
              </div>

              <div className="max-w-md mx-auto">
                <h1 className="text-2xl font-extrabold text-white">
                  Xush kelibsiz, {user?.firstName || "Tadbirkor"}!
                </h1>
                <p className="text-sm text-gray-400 mt-2 leading-relaxed">
                  Men Nexora AI — biznesingiz uchun maxsus AI yordamchisiman. Savolingizni yozing
                  yoki quyidagi tayyor mavzulardan birini tanlang:
                </p>
              </div>

              {/* Suggestions Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto text-left">
                {QUICK_SUGGESTIONS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(item.prompt)}
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
                  {msg.role === "ai" && (
                    <div className="text-xs font-bold text-cyan-400 mb-2 flex items-center gap-1.5">
                      <span>✨ Nexora AI</span>
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
                <span className="text-xs text-purple-400 font-medium">Yozmoqda</span>
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
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="glass-card rounded-2xl p-2 border border-[#8da9ff]/25 focus-within:border-purple-500 transition-colors shadow-2xl flex items-end gap-2"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Xabaringizni yozing..."
              rows={1}
              className="flex-1 bg-transparent px-3 py-2 text-white placeholder-gray-500 text-sm resize-none focus:outline-none max-h-40 font-normal leading-relaxed"
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
          <div className="text-[11px] text-gray-500 text-center mt-2 font-normal">
            Enter — yuborish, Shift+Enter — yangi qator
          </div>
        </div>
      </main>

      {/* Profile / Menu Drawer Modal */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            onClick={() => setMenuOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
          />

          <div className="relative w-full max-w-sm bg-[#0b1222] border-l border-[#8da9ff]/20 h-full p-6 flex flex-col justify-between shadow-2xl z-10 animate-fade-in-up">
            <div>
              {/* Drawer Top */}
              <div className="flex items-center justify-between pb-6 border-b border-gray-800">
                <div className="text-base font-bold text-white">Foydalanuvchi menyusi</div>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="w-8 h-8 rounded-lg bg-gray-900 text-gray-400 hover:text-white flex items-center justify-center text-sm cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Profile Card */}
              <div className="py-6 space-y-5">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600 to-cyan-500 text-black font-extrabold text-xl flex items-center justify-center shadow-lg">
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
                    <h2 className="text-lg font-bold text-white">
                      {user?.firstName} {user?.lastName}
                    </h2>
                    <p className="text-xs text-gray-400 mt-0.5">{user?.email}</p>
                  </div>
                </div>

                <div className="glass-card rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Biznes nomi</span>
                    <span className="font-semibold text-white">
                      {user?.businessName || "Nexora Business"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs pt-2 border-t border-gray-800">
                    <span className="text-gray-400">Hisob balansi</span>
                    <span className="font-bold text-cyan-400">
                      {user?.balance || "50,000 UZS"}
                    </span>
                  </div>
                </div>

                <div className="space-y-2 pt-2">
                  <Link
                    href="/profile"
                    onClick={() => setMenuOpen(false)}
                    className="w-full py-2.5 px-4 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all block text-center"
                  >
                    Profilni o'zgartirish
                  </Link>
                  <button
                    onClick={() => {
                      alert("Hisobni to'ldirish bo'limi tez kunda ishga tushadi.");
                    }}
                    className="w-full py-2.5 px-4 rounded-xl btn-gradient text-xs font-bold shadow-md cursor-pointer"
                  >
                    Hisobni to'ldirish
                  </button>
                </div>
              </div>
            </div>

            {/* Logout */}
            <div className="pt-6 border-t border-gray-800">
              <button
                onClick={() => {
                  logout();
                  setMenuOpen(false);
                }}
                className="w-full py-2.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition-colors cursor-pointer font-medium"
              >
                Log out (Chiqish)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function generateSmartReply(userText: string): string {
  const lower = userText.toLowerCase();

  if (lower.includes("savdo") || lower.includes("daromad")) {
    return `Savdo hajmini oshirish bo'yicha tavsiyalar:

1. **Mavjud mijozlar bazasi bilan ishlash:** Yangi mijoz topishdan ko'ra, mavjud mijozlarga takroriy sotuv (retention) qilish 5 barobar arzonga tushadi.
2. **O'rtacha chekni ko'tarish:** Cross-sell va Up-sell mexanizmlarini joriy eting. Masalan, mahsulotga qo'shimcha xizmat yoki to'plam (bundle) taklif qiling.
3. **Savdo voronkasi (Funnel) audit:** Mijozlar qaysi bosqichda tashlab ketayotganini aniqlang (sayt, menejer muloqoti, to'lov).

Qaysi sohada faoliyat yuritasiz? Sohangizga mos aniqroq reja tuzib berishim mumkin.`;
  }

  if (lower.includes("mijoz") || lower.includes("skript")) {
    return `Mijozlar bilan ishlash uchun 4 bosqichli universal skript:

1. **Salomlashish va diqqatni tortish:** "Assalomu alaykum [Ism]! [Kompaniya nomi]dan qo'ng'iroq qilyapman. Biznesingizda [Asosiy og'riq nuqtasi] bo'yicha qulay yechim tayyorlagan edik."
2. **Ehtiyojni aniqlash:** "Hozirgi vaqtda sizda [muammo] qanday hal qilinmoqda? Qanday qiyinchiliklar bor?"
3. **Qiymat taklifi:** "Aynan shu holat uchun bizning yechimimiz vaqtni 40% ga tejaydi va xarajatni kamaytiradi."
4. **Harakatga chaqirish (CTA):** "Sizga batafsil ko'rsatib berishimiz uchun ertaga soat 11:00 da 10 daqiqa vaqtingiz bormi?"`;
  }

  if (lower.includes("xarajat") || lower.includes("moliya")) {
    return `Xarajatlarni optimallashtirish va rentabellikni oshirish yo'llari:

1. **Doimiy va o'zgaruvchan xarajatlar tahlili:** Oxirgi 3 oylik barcha xarajatlarni 3 toifaga ajrating: Foyda keltiruvchi, Majburiy, Foydasiz.
2. **Raqamlashtirish va avtomatlashtirish:** Qo'lda bajariladigan hisob-kitob va takrorlanuvchi amallarni Nexora AI orqali avtomatlashtiring.
3. **Ta'minotchilar bilan qayta muzokara:** Katta hajm yoki oldindan to'lov hisobiga chegirma talab qiling.`;
  }

  return `Savolingiz qabul qilindi. 

Nexora AI biznes tahlilchisi sifatida bu mavzuda quyidagi asosiy tavsiyalarni beradi:
- Jarayonlarni bosqichma-bosqich rejalashtirish va har bir qadam uchun KPI belgilash;
- Jamoa a'zolari o'rtasida mas'uliyatni aniq taqsimlash;
- Natijalarni haftalik monitoring qilib borish.

Ushbu yo'nalish bo'yicha batafsilroq ma'lumot bersangiz, biznesingizga to'g'ri keladigan amaliy yechim tayyorlab beraman.`;
}
