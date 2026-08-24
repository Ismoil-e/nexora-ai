"use client";

import Sidebar from "@/components/Sidebar";
import { useState } from "react";
import { orchestrate } from "@/lib/api";

export default function OrchestratorPage() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await orchestrate({ message: input });
      setResult(res);
    } catch (err: any) {
      setResult({ success: false, error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        <h1 className="text-2xl font-bold text-white mb-2">🎯 AI Orchestrator</h1>
        <p className="text-gray-500 mb-6">
          Murakkab so&apos;rovlar orqali avtomatik agentlarni tanlaydi, reja tuzadi va bajaradi
        </p>

        {/* Input */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Murakkab so&apos;rovni yozing... Masalan: 'O&apos;tgan chorakdagi sotish natijalarini tahlil qilib, sabablarni aniqla va hisobot tayyorla'"
            rows={4}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            className="mt-3 px-6 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          >
            {loading ? "⏳ Orchestrate qilinmoqda..." : "🎯 Orchestrate"}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="space-y-4">
            {/* Status */}
            <div className={`flex items-center gap-3 p-4 rounded-xl border ${
              result.success
                ? "bg-green-900/20 border-green-800"
                : "bg-red-900/20 border-red-800"
            }`}>
              <span className="text-2xl">{result.success ? "✅" : "❌"}</span>
              <div>
                <div className="font-medium text-white">
                  {result.success ? "Muvaffaqiyatli" : "Xatolik"}
                </div>
                <div className="text-sm text-gray-400">
                  {result.agent_key && `Agent: ${result.agent_key} · `}
                  {result.tokens_used} tokens · {result.duration_ms}ms
                  {result.cost > 0 && ` · $${result.cost}`}
                </div>
              </div>
            </div>

            {/* Output */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Natija</h3>
              <div className="text-gray-200 text-sm whitespace-pre-wrap leading-relaxed">
                {result.output}
              </div>
            </div>

            {/* Plan */}
            {result.plan && result.plan.subtasks && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-3">
                  📋 Reja ({result.plan.subtasks.length} qadam)
                </h3>
                <div className="space-y-2">
                  {result.plan.subtasks.map((st: any, i: number) => (
                    <div key={st.id || i} className="flex items-center gap-3">
                      <span className="w-6 h-6 bg-gray-800 rounded-full flex items-center justify-center text-xs text-gray-400">
                        {i + 1}
                      </span>
                      <span className="text-sm text-gray-300">{st.description}</span>
                      <span className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-500">
                        🤖 {st.agent}
                      </span>
                      <StatusBadge status={st.status} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timeline */}
            {result.timeline && result.timeline.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-3">📊 Execution Timeline</h3>
                <div className="space-y-2">
                  {result.timeline.map((step: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span className="text-lg">{step.icon || "•"}</span>
                      <span className="text-gray-300 flex-1">{step.label}</span>
                      {step.duration_ms > 0 && (
                        <span className="text-gray-600 text-xs">{step.duration_ms}ms</span>
                      )}
                      {step.tokens && (
                        <span className="text-gray-600 text-xs">{step.tokens} tok</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Citations */}
            {result.citations && result.citations.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="text-sm font-medium text-gray-400 mb-3">📚 Manbalar ({result.citations.length})</h3>
                <div className="space-y-2">
                  {result.citations.map((c: any, i: number) => (
                    <div key={i} className="p-3 bg-gray-800 rounded-lg text-sm">
                      <span className="text-purple-400">{c.source_type}</span>
                      <span className="text-gray-500 mx-2">·</span>
                      <span className="text-gray-400">{(c.snippet || "").slice(0, 120)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-900/50 text-green-400",
    running: "bg-blue-900/50 text-blue-400",
    failed: "bg-red-900/50 text-red-400",
    created: "bg-gray-800 text-gray-400",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs ${colors[status] || "bg-gray-800 text-gray-500"}`}>
      {status}
    </span>
  );
}
