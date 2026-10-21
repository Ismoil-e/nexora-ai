"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const ADMIN_NAV = [
  { label: "Bosh sahifa", href: "/admin", icon: "🏠" },
  { label: "AI Chat", href: "/admin/chat", icon: "💬" },
  { label: "Orchestrator", href: "/admin/orchestrator", icon: "🎯" },
  { label: "Agentlar", href: "/admin/agents", icon: "🤖" },
  { label: "Execution Traces", href: "/admin/traces", icon: "📊" },
  { label: "Tasdiqlashlar", href: "/admin/approvals", icon: "✅" },
  { label: "Modellar", href: "/admin/models", icon: "🧠" },
  { label: "AI Xarajatlar", href: "/admin/usage", icon: "📈" },
];

export default function AdminSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-xl font-bold">
          <span className="text-blue-400">Nexora</span>{" "}
          <span className="text-gray-300">AI</span>
        </h1>
        <div className="flex items-center gap-2 mt-2">
          <span className="px-2 py-0.5 bg-blue-600/20 text-blue-400 text-xs rounded-full font-medium">
            👑 Admin
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {ADMIN_NAV.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User & Logout */}
      <div className="p-4 border-t border-gray-800">
        <div className="text-sm text-gray-400 mb-2">{user?.name}</div>
        <button
          onClick={logout}
          className="w-full text-left text-sm text-gray-500 hover:text-red-400 transition-colors cursor-pointer"
        >
          🚪 Chiqish
        </button>
      </div>
    </aside>
  );
}
