"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "AI Chat", href: "/chat", icon: "💬" },
  { label: "Orchestrator", href: "/orchestrator", icon: "🎯" },
  { label: "Agents", href: "/agents", icon: "🤖" },
  { label: "Execution Traces", href: "/traces", icon: "📊" },
  { label: "Approvals", href: "/approvals", icon: "✅" },
  { label: "Models", href: "/models", icon: "🧠" },
  { label: "AI Usage", href: "/usage", icon: "📈" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-xl font-bold">
          <span className="text-blue-400">Nexora</span>{" "}
          <span className="text-gray-300">AI</span>
        </h1>
        <p className="text-xs text-gray-500 mt-1">Control Center</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
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

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-600">Nexora AI v1.0</div>
      </div>
    </aside>
  );
}
