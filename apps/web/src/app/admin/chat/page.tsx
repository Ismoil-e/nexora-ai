"use client";

import AdminSidebar from "@/components/AdminSidebar";
import { useEffect, useRef, useState } from "react";
import { orchestrate } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  timeline?: any[];
  citations?: any[];
  tokens?: number;
  duration_ms?: number;
}

export default function AdminChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = await orchestrate({
        message: input,
        metadata: selectedAgent ? { single_agent: true, agent_key: selectedAgent } : {},
      });

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.output || result.error || "Javob olinmadi",
        agent: result.agent_key,
        timeline: result.timeline,
        citations: result.citations,
        tokens: result.tokens_used,
        duration_ms: result.duration_ms,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Xatolik: ${err.message}`,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="ml-64 flex-1 flex flex-col h-screen">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h1 className="text-xl font-bold text-white">AI Chat</h1>
            <p className="text-sm text-gray-500">Orchestrator orqali suhbat</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-500">Agent:</label>
            <select
              value={selectedAgent || ""}
              onChange={(e) => setSelectedAgent(e.target.value || null)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
            >
              <option value="">Avtomatik tanlash</option>
              <option value="chat">Chat Agent</option>
              <option value="document">Document Agent</option>
              <option value="analytics">Analytics Agent</option>
              <option value="knowledge">Knowledge Agent</option>
              <option value="search">Search Agent</option>
              <option value="planning">Planning Agent</option>
              <option value="task">Task Agent</option>
              <option value="monitoring">Monitoring Agent</option>
            </select>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-6xl mb-4">🤖</div>
                <h2 className="text-xl font-semibold text-gray-300">Nexora AI ga xush kelibsiz</h2>
                <p className="text-gray-500 mt-2">Murakkab savollaringizni yozing — Orchestrator avtomatik agentlarni tanlaydi</p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-3xl rounded-2xl px-4 py-3 ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-200"}`}>
                {msg.agent && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-purple-600/30 text-purple-300 rounded-full text-xs">🤖 {msg.agent}</span>
                    {msg.tokens && <span className="text-xs text-gray-500">{msg.tokens} tokens · {msg.duration_ms}ms</span>}
                  </div>
                )}
                <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-gray-700/50">
                    <div className="text-xs text-gray-500 mb-1">Manbalar:</div>
                    <div className="flex flex-wrap gap-1">
                      {msg.citations.map((c: any, i: number) => (
                        <span key={i} className="px-2 py-0.5 bg-gray-700/50 rounded text-xs text-gray-400">
                          {c.source_type || "doc"}: {(c.snippet || "").slice(0, 50)}...
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {msg.timeline && msg.timeline.length > 0 && (
                  <details className="mt-3">
                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">📊 Execution trace ({msg.timeline.length} qadam)</summary>
                    <div className="mt-2 space-y-1">
                      {msg.timeline.map((step: any, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span>{step.icon || "•"}</span>
                          <span className="text-gray-400">{step.label}</span>
                          {step.duration_ms > 0 && <span className="text-gray-600">({step.duration_ms}ms)</span>}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: "0.2s" }} />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: "0.4s" }} />
                  <span className="text-sm text-gray-400 ml-2">Orchestrator ishlayapti...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-3 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="Savolingizni yozing..."
              disabled={loading}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Yuborish
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
