"use client";

import AdminSidebar from "@/components/AdminSidebar";
import { useEffect, useState } from "react";
import { listModels, routeModel } from "@/lib/api";

export default function AdminModelsPage() {
  const [models, setModels] = useState<any[]>([]);
  const [filter, setFilter] = useState("");
  const [testInput, setTestInput] = useState("");
  const [routingResult, setRoutingResult] = useState<any>(null);
  const [routingLoading, setRoutingLoading] = useState(false);

  useEffect(() => {
    listModels().then((d) => setModels(d?.models || [])).catch(() => {});
  }, []);

  const filtered = filter ? models.filter((m) => m.provider === filter) : models;
  const providers = [...new Set(models.map((m) => m.provider))];

  const testRouting = async () => {
    if (!testInput.trim()) return;
    setRoutingLoading(true);
    try { const result = await routeModel({ user_input: testInput }); setRoutingResult(result); }
    catch (err: any) { setRoutingResult({ error: err.message }); }
    finally { setRoutingLoading(false); }
  };

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="ml-64 flex-1 p-8">
        <h1 className="text-2xl font-bold text-white mb-2">🧠 AI Modellar</h1>
        <p className="text-gray-500 mb-6">Mavjud modellar, imkoniyatlari va model routing testi</p>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-sm font-medium text-gray-400 mb-3">Model Routing Testi</h2>
          <div className="flex gap-3">
            <input type="text" value={testInput} onChange={(e) => setTestInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && testRouting()}
              placeholder="So'rov yozing — qaysi model tanlanadi?"
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500" />
            <button onClick={testRouting} disabled={routingLoading}
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm disabled:opacity-50 transition-colors">
              {routingLoading ? "⏳" : "🎯 Route"}
            </button>
          </div>
          {routingResult && !routingResult.error && (
            <div className="mt-4 p-4 bg-gray-800 rounded-lg">
              <div className="flex items-center gap-4">
                <div><div className="text-xs text-gray-500">Provider</div><div className="text-sm text-blue-400 font-medium">{routingResult.provider}</div></div>
                <div><div className="text-xs text-gray-500">Model</div><div className="text-sm text-green-400 font-medium">{routingResult.model}</div></div>
                <div><div className="text-xs text-gray-500">Temperature</div><div className="text-sm text-gray-300">{routingResult.temperature}</div></div>
              </div>
              <div className="mt-2 text-xs text-gray-500">{routingResult.reasoning}</div>
            </div>
          )}
        </div>

        <div className="flex gap-2 mb-4">
          <button onClick={() => setFilter("")} className={`px-3 py-1.5 rounded-lg text-sm ${!filter ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400"}`}>
            Barchasi ({models.length})
          </button>
          {providers.map((p) => (
            <button key={p} onClick={() => setFilter(p)} className={`px-3 py-1.5 rounded-lg text-sm ${filter === p ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400"}`}>
              {p}
            </button>
          ))}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Context</th>
                <th className="px-4 py-3">Cost</th>
                <th className="px-4 py-3">Imkoniyatlar</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((model: any, i: number) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="px-4 py-3"><span className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400">{model.provider}</span></td>
                  <td className="px-4 py-3 text-sm text-gray-300 font-medium">{model.model}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{(model.context_window || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">${model.cost_per_1k_input} / ${model.cost_per_1k_output}</td>
                  <td className="px-4 py-3 flex gap-1">
                    {model.supports_tools && <span className="px-1.5 py-0.5 bg-blue-900/30 text-blue-400 rounded text-xs">Tools</span>}
                    {model.supports_vision && <span className="px-1.5 py-0.5 bg-blue-900/30 text-blue-400 rounded text-xs">Vision</span>}
                    {model.supports_code && <span className="px-1.5 py-0.5 bg-blue-900/30 text-blue-400 rounded text-xs">Code</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
