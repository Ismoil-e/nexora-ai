"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { useEffect, useState } from "react";

const ADMIN_ACTIONS = [
  { label: "AI Chat", href: "/admin/chat", icon: "💬", desc: "AI bilan suhbat", color: "bg-blue-600" },
  { label: "Orchestrator", href: "/admin/orchestrator", icon: "🎯", desc: "Murakkab so'rovlar", color: "bg-purple-600" },
  { label: "Agentlar", href: "/admin/agents", icon: "🤖", desc: "Agent boshqaruvi", color: "bg-green-600" },
  { label: "Modellar", href: "/admin/models", icon: "🧠", desc: "AI model konfiguratsiya", color: "bg-orange-600" },
  { label: "Tasdiqlashlar", href: "/admin/approvals", icon: "✅", desc: "Harakat tasdiqlash", color: "bg-yellow-600" },
  { label: "Xarajatlar", href: "/admin/usage", icon: "📈", desc: "AI statistika", color: "bg-cyan-600" },
  { label: "Execution Traces", href: "/admin/traces", icon: "📊", desc: "Bajarilgan operatsiyalar", color: "bg-pink-600" },
];

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const [greeting, setGreeting] = useState("");

  useEffect(() => {
    const h = new Date().getHours();
    if (h < 12) setGreeting("Xayrli ertalab");
    else if (h < 18) setGreeting("Xush kun o'rtasi");
    else setGreeting("Xush kechqurun");
  }, []);

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Top Bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">👑</span>
          <div>
            <span className="text-blue-400 font-bold text-lg">Nexora</span>
            <span className="text-gray-300 font-bold text-lg ml-1">AI</span>
            <span className="ml-3 px-2 py-0.5 bg-blue-600/20 text-blue-400 text-xs rounded-full font-medium">
              Admin
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{user?.name}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-red-400 transition-colors cursor-pointer"
          >
            Chiqish
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            {greeting}, {user?.name?.split(" ")[0]}
          </h1>
          <p className="text-gray-400 mt-2">
            Admin boshqaruv paneli — barcha tizimlarni boshqaring
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard title="Agentlar" value="12" icon="🤖" color="text-blue-400" />
          <StatCard title="Modellar" value="10" icon="🧠" color="text-purple-400" />
          <StatCard title="So'rovlar (24h)" value="156" icon="📊" color="text-green-400" />
          <StatCard title="Xarajat (24h)" value="$12.40" icon="💰" color="text-yellow-400" />
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-300 mb-4">Tez harakatlar</h2>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {ADMIN_ACTIONS.map((action) => (
              <Link
                key={action.href}
                href={action.href}
                className="flex items-center gap-4 p-5 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-all group"
              >
                <div className={`w-12 h-12 rounded-lg ${action.color} flex items-center justify-center text-xl group-hover:scale-110 transition-transform`}>
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

        {/* System Status */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gray-300 mb-4">Tizim holati</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatusItem name="Backend API" status="active" />
            <StatusItem name="PostgreSQL" status="active" />
            <StatusItem name="Redis" status="active" />
            <StatusItem name="Celery Workers" status="active" />
            <StatusItem name="MinIO Storage" status="active" />
            <StatusItem name="AI Providers" status="warning" />
            <StatusItem name="Nginx" status="active" />
            <StatusItem name="Monitoring" status="active" />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }: { title: string; value: string; icon: string; color: string }) {
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

function StatusItem({ name, status }: { name: string; status: string }) {
  const colors: Record<string, string> = {
    active: "bg-green-500",
    warning: "bg-yellow-500",
    error: "bg-red-500",
  };
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
      <div className={`w-2.5 h-2.5 rounded-full ${colors[status] || "bg-gray-500"}`} />
      <span className="text-sm text-gray-300">{name}</span>
    </div>
  );
}
