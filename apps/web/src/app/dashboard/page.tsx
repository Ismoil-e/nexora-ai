"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { useEffect, useState } from "react";

const CUSTOMER_ACTIONS = [
  { label: "AI Chat", href: "/dashboard/chat", icon: "💬", desc: "AI bilan suhbat boshlang", color: "bg-blue-600" },
  { label: "Hujjatlarim", href: "/dashboard/documents", icon: "📄", desc: "Yuklangan hujjatlar", color: "bg-purple-600" },
  { label: "Bazalarim", href: "/dashboard/knowledge", icon: "📚", desc: "Bilim bazalari", color: "bg-green-600" },
];

export default function CustomerDashboard() {
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
          <span className="text-2xl">💬</span>
          <div>
            <span className="text-blue-400 font-bold text-lg">Nexora</span>
            <span className="text-gray-300 font-bold text-lg ml-1">AI</span>
            <span className="ml-3 px-2 py-0.5 bg-green-600/20 text-green-400 text-xs rounded-full font-medium">
              Mijoz
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

      <div className="max-w-4xl mx-auto p-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            {greeting}, {user?.name?.split(" ")[0]} 👋
          </h1>
          <p className="text-gray-400 mt-2">
            Nexora AI ga xush kelibsiz — qanday yordam bera olaman?
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {CUSTOMER_ACTIONS.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className="flex flex-col items-center gap-3 p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-all group text-center"
            >
              <div className={`w-16 h-16 rounded-xl ${action.color} flex items-center justify-center text-3xl group-hover:scale-110 transition-transform`}>
                {action.icon}
              </div>
              <div>
                <div className="font-medium text-white text-lg">{action.label}</div>
                <div className="text-sm text-gray-500 mt-1">{action.desc}</div>
              </div>
            </Link>
          ))}
        </div>

        {/* Suggested Questions */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gray-300 mb-4">💡 Sinab ko'ring</h2>
          <div className="space-y-3">
            {[
              "Nexora AI nima qila oladi?",
              "Hujjatlarimni tahlil qilib ber",
              "Xarajatlar hisobotini tayyorla",
              "Eng so'nggi yangiliklar nima?",
            ].map((q, i) => (
              <Link
                key={i}
                href={`/dashboard/chat?q=${encodeURIComponent(q)}`}
                className="block p-3 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-300 hover:border-blue-500 hover:bg-blue-500/5 transition-all text-sm"
              >
                → {q}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
