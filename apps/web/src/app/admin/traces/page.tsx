"use client";

import AdminSidebar from "@/components/AdminSidebar";
import { useEffect, useState } from "react";
import { listTraces, getTimeline } from "@/lib/api";

export default function AdminTracesPage() {
  const [traces, setTraces] = useState<any[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);

  useEffect(() => {
    listTraces(50).then((d) => setTraces(d || [])).catch(() => {});
  }, []);

  const selectTrace = async (trace: any) => {
    setSelectedTrace(trace);
    try {
      const t = await getTimeline(trace.id);
      setTimeline(t?.timeline || []);
    } catch { setTimeline([]); }
  };

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="ml-64 flex-1 p-8">
        <h1 className="text-2xl font-bold text-white mb-2">📊 Execution Traces</h1>
        <p className="text-gray-500 mb-6">Orchestration jarayonining to&apos;liq vizual timelinei</p>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden max-h-[80vh] overflow-y-auto">
              {traces.length === 0 ? (
                <div className="p-8 text-center text-gray-500">Hali trace yo&apos;q</div>
              ) : traces.map((trace: any) => (
                <div key={trace.id} onClick={() => selectTrace(trace)}
                  className={`p-4 border-b border-gray-800/50 cursor-pointer transition-colors ${selectedTrace?.id === trace.id ? "bg-blue-600/10 border-l-2 border-l-blue-500" : "hover:bg-gray-800/50"}`}>
                  <div className="flex items-center justify-between mb-1">
                    <StatusBadge status={trace.status} />
                    <span className="text-xs text-gray-600">{trace.duration_ms}ms</span>
                  </div>
                  <div className="text-sm text-gray-300 line-clamp-2">{trace.user_input}</div>
                  <div className="text-xs text-gray-600 mt-1">{trace.total_tokens?.toLocaleString()} tokens</div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-3">
            {selectedTrace ? (
              <div className="space-y-4">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <StatusBadge status={selectedTrace.status} />
                    <span className="text-sm text-gray-500">{selectedTrace.total_tokens?.toLocaleString()} tokens</span>
                  </div>
                  <p className="text-gray-300 text-sm">{selectedTrace.user_input}</p>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                  <h3 className="text-sm font-medium text-gray-400 mb-4">Timeline</h3>
                  <div className="relative">
                    <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-800" />
                    <div className="space-y-3">
                      {timeline.map((step: any, i: number) => (
                        <div key={i} className="flex items-start gap-4 relative">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm z-10 ${step.success ? "bg-gray-800" : "bg-red-900/50"}`}>
                            {step.icon || "•"}
                          </div>
                          <div className="flex-1 pb-2">
                            <div className="text-sm text-gray-300">{step.label}</div>
                            {step.agent && <span className="text-xs text-purple-400">🤖 {step.agent}</span>}
                            {step.duration_ms > 0 && <span className="text-xs text-gray-600 ml-2">{step.duration_ms}ms</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500">Trace tanlang</div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-900/50 text-green-400",
    running: "bg-blue-900/50 text-blue-400",
    failed: "bg-red-900/50 text-red-400",
    pending: "bg-yellow-900/50 text-yellow-400",
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || "bg-gray-800 text-gray-400"}`}>{status}</span>;
}
