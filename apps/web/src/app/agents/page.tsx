"use client";

import Sidebar from "@/components/Sidebar";
import { useEffect, useState } from "react";
import { listAgentCatalog, listCompanyAgents } from "@/lib/api";

const AGENT_ICONS: Record<string, string> = {
  chat: "💬",
  document: "📄",
  analytics: "📊",
  knowledge: "📚",
  search: "🔍",
  planning: "📋",
  task: "✅",
  notification: "🔔",
  monitoring: "📡",
};

export default function AgentsPage() {
  const [catalog, setCatalog] = useState<any[]>([]);
  const [companyAgents, setCompanyAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<any>(null);

  useEffect(() => {
    listAgentCatalog().then((d) => setCatalog(d?.agents || [])).catch(() => {});
    listCompanyAgents().then((d) => setCompanyAgents(d?.items || [])).catch(() => {});
  }, []);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        <h1 className="text-2xl font-bold text-white mb-2">🤖 Agentlar</h1>
        <p className="text-gray-500 mb-6">AI agentlarni boshqarish — registry, imkoniyatlar, vositalar</p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Agent Catalog */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-gray-300 mb-4">Framework Agentlar</h2>
            <div className="grid grid-cols-2 gap-4">
              {catalog.map((agent: any) => (
                <div
                  key={agent.agent_key}
                  onClick={() => setSelectedAgent(agent)}
                  className={`p-4 bg-gray-900 border rounded-xl cursor-pointer transition-colors ${
                    selectedAgent?.agent_key === agent.agent_key
                      ? "border-blue-500"
                      : "border-gray-800 hover:border-gray-700"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{AGENT_ICONS[agent.agent_key] || "🤖"}</span>
                    <div>
                      <div className="font-medium text-white">{agent.display_name}</div>
                      <div className="text-xs text-gray-500">{agent.agent_key}</div>
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-gray-400 line-clamp-2">{agent.description}</p>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {(agent.capabilities || []).map((cap: string) => (
                      <span key={cap} className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-500">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Company Agents */}
            {companyAgents.length > 0 && (
              <>
                <h2 className="text-lg font-semibold text-gray-300 mt-8 mb-4">Kompaniya Agentlari</h2>
                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                        <th className="px-4 py-3">Nomi</th>
                        <th className="px-4 py-3">Provider</th>
                        <th className="px-4 py-3">Model</th>
                        <th className="px-4 py-3">Holat</th>
                      </tr>
                    </thead>
                    <tbody>
                      {companyAgents.map((agent: any) => (
                        <tr key={agent.id} className="border-b border-gray-800/50">
                          <td className="px-4 py-3 text-sm text-gray-300">{agent.name}</td>
                          <td className="px-4 py-3 text-sm text-gray-400">{agent.ai_provider}</td>
                          <td className="px-4 py-3 text-sm text-gray-400">{agent.model}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded-full text-xs ${
                              agent.is_active ? "bg-green-900/50 text-green-400" : "bg-gray-800 text-gray-500"
                            }`}>
                              {agent.is_active ? "Faol" : "Nofaol"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>

          {/* Agent Detail Panel */}
          <div>
            <h2 className="text-lg font-semibold text-gray-300 mb-4">Agent Tafsilotlari</h2>
            {selectedAgent ? (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{AGENT_ICONS[selectedAgent.agent_key] || "🤖"}</span>
                  <div>
                    <div className="font-bold text-white text-lg">{selectedAgent.display_name}</div>
                    <div className="text-sm text-gray-500">v{selectedAgent.version}</div>
                  </div>
                </div>
                <p className="text-sm text-gray-400 mb-4">{selectedAgent.description}</p>

                <div className="space-y-3">
                  <DetailSection title="Imkoniyatlar" items={selectedAgent.capabilities} />
                </div>
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
                Agentni tanlang
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function DetailSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase mb-2">{title}</div>
      <div className="flex flex-wrap gap-1">
        {(items || []).length > 0 ? (
          items.map((item: string) => (
            <span key={item} className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-400">
              {item}
            </span>
          ))
        ) : (
          <span className="text-xs text-gray-600">Yo&apos;q</span>
        )}
      </div>
    </div>
  );
}
