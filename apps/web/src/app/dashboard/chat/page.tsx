"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function CustomerChatPage() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Salom! Men Nexora AI yordamchisiman. Sizga qanday yordam bera olaman? 😊",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // Demo: simulate AI response
    setTimeout(() => {
      const responses = [
        "Yaxshi savol! Nexora AI sizning hujjatlaringizni tahlil qilishi, bilim bazangizdan qidirishi va turli AI modellardan foydalanishi mumkin. 🧠",
        "Men sizga yordam berishga tayyorman. Savolingizni batafsilroq yozsangiz, aniqroq javob beraman. ✨",
        "Nexora AI — bu multi-agent tizim. Turli mutaxassis agentlar birgalikda ishlaydi va eng yaxshi natijani beradi. 🤖",
        "Hujjatlaringizni yuklang, men ularni tahlil qilaman va sizga muhim ma'lumotlarni topib beraman. 📄",
      ];
      const aiMsg: Message = {
        role: "assistant",
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
      setLoading(false);
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
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
          <span className="text-lg">💬</span>
          <span className="text-white font-medium">AI Chat</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{user?.name}</span>
          <button onClick={logout} className="text-sm text-gray-500 hover:text-red-400 cursor-pointer">
            Chiqish
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] p-4 rounded-2xl ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-gray-800 text-gray-200 rounded-bl-sm border border-gray-700"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="text-xs text-blue-400 mb-2 font-medium">Nexora AI</div>
                )}
                <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                <div className={`text-xs mt-2 ${msg.role === "user" ? "text-blue-200" : "text-gray-500"}`}>
                  {msg.timestamp.toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-sm p-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse [animation-delay:0.2s]" />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Xabaringizni yozing..."
            rows={1}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 text-sm resize-none focus:outline-none focus:border-blue-500 transition-colors"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium text-sm transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            Yuborish
          </button>
        </div>
      </div>
    </div>
  );
}
