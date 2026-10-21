"use client";

import AdminSidebar from "@/components/AdminSidebar";
import { useEffect, useState } from "react";
import { getUsageSummary } from "@/lib/api";

export default function AdminUsagePage() {
  const [usage, setUsage] = useState<any>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    getUsageSummary(days).then((d) => setUsage(d)).catch(() => {});
  }, [days]);

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="ml-64 flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">📈 AI Usage Dashboard</h1>
            <p className="text-gray-500">AI resurslari ishlatilishi va xarajatlari</p>
          </div>
          <div className="flex gap-2">
            {[7, 30, 90].map((d) => (
              <button key={d} onClick={() => setDays(d)}
                className={`px-3 py-1.5 rounded-lg text-sm ${days === d ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400"}`}>
                {d} kun
              </button>
            ))}
          </div>
        </div>

        {usage ? (
          <>
            <div className="grid grid-cols-4 gap-4 mb-6">
              <StatCard title="So'rovlar" value={usage.request_count?.toLocaleString() || "0"} icon="📊" />
              <StatCard title="Tokenlar" value={usage.total_tokens?.toLocaleString() || "0"} icon="🔤" />
              <StatCard title="Xarajat" value={`$${usage.total_cost || 0}`} icon="💰" />
              <StatCard title="Muvaffaqiyat" value={`${usage.success_rate || 0}%`} icon="✅" />
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Provider bo&apos;yicha</h3>
                {usage.by_provider?.length > 0 ? (
                  <div className="space-y-3">
                    {usage.by_provider.map((p: any) => (
                      <div key={p.key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-300">{p.key}</span>
                          <span className="text-xs text-gray-500">{p.tokens?.toLocaleString()} tok</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${Math.min(100, (p.tokens / Math.max(usage.total_tokens, 1)) * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-sm text-gray-600">Ma&apos;lumot yo&apos;q</div>}
              </div>

              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Model bo&apos;yicha</h3>
                {usage.by_model?.length > 0 ? (
                  <div className="space-y-3">
                    {usage.by_model.map((m: any) => (
                      <div key={m.key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-300">{m.key}</span>
                          <span className="text-xs text-gray-500">${m.cost}</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${Math.min(100, (m.tokens / Math.max(usage.total_tokens, 1)) * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-sm text-gray-600">Ma&apos;lumot yo&apos;q</div>}
              </div>
            </div>
          </>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500">Yuklanmoqda...</div>
        )}
      </main>
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string; value: string; icon: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between">
        <span className="text-xl">{icon}</span>
        <span className="text-xl font-bold text-white">{value}</span>
      </div>
      <div className="mt-2 text-sm text-gray-500">{title}</div>
    </div>
  );
}
