"use client";

import Sidebar from "@/components/Sidebar";
import { useEffect, useState } from "react";
import { getUsageSummary } from "@/lib/api";

export default function UsagePage() {
  const [usage, setUsage] = useState<any>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    getUsageSummary(days).then((d) => setUsage(d)).catch(() => {});
  }, [days]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">📈 AI Usage Dashboard</h1>
            <p className="text-gray-500">AI resurslari ishlatilishi va xarajatlari</p>
          </div>
          <div className="flex gap-2">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 rounded-lg text-sm ${days === d ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400"}`}
              >
                {d} kun
              </button>
            ))}
          </div>
        </div>

        {usage ? (
          <>
            {/* Overview Cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              <StatCard title="Jami so'rovlar" value={usage.request_count?.toLocaleString() || "0"} icon="📊" />
              <StatCard title="Jami tokenlar" value={usage.total_tokens?.toLocaleString() || "0"} icon="🔤" />
              <StatCard title="Jami xarajat" value={`$${usage.total_cost || 0}`} icon="💰" />
              <StatCard title="Muvaffaqiyat" value={`${usage.success_rate || 0}%`} icon="✅" />
            </div>

            <div className="grid grid-cols-2 gap-6">
              {/* Provider Breakdown */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Provider bo&apos;yicha</h3>
                {usage.by_provider?.length > 0 ? (
                  <div className="space-y-3">
                    {usage.by_provider.map((p: any) => (
                      <div key={p.key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-300">{p.key}</span>
                          <span className="text-xs text-gray-500">{p.tokens?.toLocaleString()} tok · {p.count} so&apos;rov</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min(100, (p.tokens / Math.max(usage.total_tokens, 1)) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600">Ma&apos;lumot yo&apos;q</div>
                )}
              </div>

              {/* Model Breakdown */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Model bo&apos;yicha</h3>
                {usage.by_model?.length > 0 ? (
                  <div className="space-y-3">
                    {usage.by_model.map((m: any) => (
                      <div key={m.key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-300">{m.key}</span>
                          <span className="text-xs text-gray-500">{m.tokens?.toLocaleString()} tok · ${m.cost}</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min(100, (m.tokens / Math.max(usage.total_tokens, 1)) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600">Ma&apos;lumot yo&apos;q</div>
                )}
              </div>

              {/* Task Type Breakdown */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Task turi bo&apos;yicha</h3>
                {usage.by_task_type?.length > 0 ? (
                  <div className="space-y-3">
                    {usage.by_task_type.map((t: any) => (
                      <div key={t.key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-300">{t.key}</span>
                          <span className="text-xs text-gray-500">{t.count} so&apos;rov</span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min(100, (t.count / Math.max(usage.request_count, 1)) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600">Ma&apos;lumot yo&apos;q</div>
                )}
              </div>

              {/* Daily Trend */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Kunlik trend</h3>
                {usage.daily_trend?.length > 0 ? (
                  <div className="space-y-2">
                    {usage.daily_trend.slice(-14).map((day: any) => (
                      <div key={day.date} className="flex items-center gap-3">
                        <span className="text-xs text-gray-500 w-20">{day.date}</span>
                        <div className="flex-1 bg-gray-800 rounded-full h-3">
                          <div
                            className="bg-cyan-500 h-3 rounded-full"
                            style={{
                              width: `${Math.min(100, (day.tokens / Math.max(usage.total_tokens / Math.max(usage.daily_trend?.length || 1, 1), 1)) * 50)}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-16 text-right">{day.tokens?.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-600">Ma&apos;lumot yo&apos;q</div>
                )}
              </div>
            </div>

            {/* Summary Stats */}
            <div className="mt-6 bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-sm font-medium text-gray-400 mb-3">O&apos;rtacha ko&apos;rsatkichlar</h3>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-2xl font-bold text-white">{usage.avg_tokens_per_request?.toLocaleString()}</div>
                  <div className="text-xs text-gray-500">O&apos;rtacha token/so&apos;rov</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-white">${usage.avg_cost_per_request}</div>
                  <div className="text-xs text-gray-500">O&apos;rtacha xarajat/so&apos;rov</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-white">{usage.period_days}</div>
                  <div className="text-xs text-gray-500">Davr (kun)</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-400">{usage.success_rate}%</div>
                  <div className="text-xs text-gray-500">Muvaffaqiyat darajasi</div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500">
            Ma&apos;lumotlar yuklanmoqda...
          </div>
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
