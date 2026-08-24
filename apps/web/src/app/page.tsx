"use client";

import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { useEffect, useState } from "react";
import { listTraces, getUsageSummary } from "@/lib/api";

const QUICK_ACTIONS = [
  { label: "AI Chat", href: "/chat", icon: "💬", desc: "Suhbat boshlash", color: "bg-blue-600" },
  { label: "Orchestrator", href: "/orchestrator", icon: "🎯", desc: "Murakkab so'rov", color: "bg-purple-600" },
  { label: "Agents", href: "/agents", icon: "🤖", desc: "Agentlarni boshqarish", color: "bg-green-600" },
  { label: "Models", href: "/models", icon: "🧠", desc: "AI modellar", color: "bg-orange-600" },
  { label: "Approvals", href: "/approvals", icon: "✅", desc: "Tasdiqlashlar", color: "bg-yellow-600" },
  { label: "Usage", href: "/usage", icon: "📈", desc: "AI statistika", color: "bg-cyan-600" },
];

export default function HomePage() {
  const [recentTraces, setRecentTraces] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    listTraces(5).then((data) => setRecentTraces(data || [])).catch(() => {});
    getUsageSummary(7).then((data) => setStats(data)).catch(() => {});
  }, []);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">AI Control Center</h1>
          <p className="text-gray-400 mt-2">Nexora AI — markaziy boshqaruv paneli</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard
            title="So'rovlar (7 kun)"
            value={stats?.request_count || "—"}
            icon="📊"
            color="text-blue-400"
          />
          <StatCard
            title="Tokenlar (7 kun)"
            value={stats?.total_tokens ? stats.total_tokens.toLocaleString() : "—"}
            icon="🔤"
            color="text-green-400"
          />
          <StatCard
            title="Xarajat (7 kun)"
            value={stats?.total_cost ? `$${stats.total_cost}` : "—"}
            icon="💰"
            color="text-yellow-400"
          />
          <StatCard
            title="Muvaffaqiyat"
            value={stats?.success_rate ? `${stats.success_rate}%` : "—"}
            icon="✅"
            color="text-cyan-400"
          />
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-300 mb-4">Tez harakatlar</h2>
          <div className="grid grid-cols-3 gap-4">
            {QUICK_ACTIONS.map((action) => (
              <Link
                key={action.href}
                href={action.href}
                className="flex items-center gap-4 p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-colors"
              >
                <div className={`w-12 h-12 rounded-lg ${action.color} flex items-center justify-center text-xl`}>
                  {action.icon}
                </div>
                <div>
                  <div className="font-medium text-white">{action.label}</div>
                  <div className="text-sm text-gray-500">{action.desc}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Traces */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-300">So'nggi traces</h2>
            <Link href="/traces" className="text-sm text-blue-400 hover:text-blue-300">
              Barchasini ko'rish →
            </Link>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            {recentTraces.length === 0 ? (
              <div className="p-8 text-center text-gray-500">Hali trace yo'q</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">So'rov</th>
                    <th className="px-4 py-3">Tokenlar</th>
                    <th className="px-4 py-3">Vaqt</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTraces.map((trace: any) => (
                    <tr key={trace.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="px-4 py-3">
                        <StatusBadge status={trace.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300 max-w-xs truncate">
                        {trace.user_input}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {trace.total_tokens?.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {trace.duration_ms}ms
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ title, value, icon, color }: { title: string; value: any; icon: string; color: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between">
        <span className="text-xl">{icon}</span>
        <span className={`text-2xl font-bold ${color}`}>{value}</span>
      </div>
      <div className="mt-2 text-sm text-gray-500">{title}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-900/50 text-green-400",
    running: "bg-blue-900/50 text-blue-400",
    failed: "bg-red-900/50 text-red-400",
    pending: "bg-yellow-900/50 text-yellow-400",
    partial: "bg-orange-900/50 text-orange-400",
  };
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || "bg-gray-800 text-gray-400"}`}>
      {status}
    </span>
  );
}
