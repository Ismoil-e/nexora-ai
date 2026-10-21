"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push(user.role === "admin" ? "/admin" : "/dashboard");
    }
  }, [user, router]);

  const handleLogin = (role: "admin" | "customer") => {
    login(role);
    router.push(role === "admin" ? "/admin" : "/dashboard");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-md p-8">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold">
            <span className="text-blue-400">Nexora</span>{" "}
            <span className="text-gray-300">AI</span>
          </h1>
          <p className="text-gray-500 mt-3 text-sm">Multi-tenant AI SaaS Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-white text-center mb-2">
            Xush kelibsiz
          </h2>
          <p className="text-gray-500 text-center text-sm mb-8">
            Tizimga kirish uchun rolni tanlang
          </p>

          <div className="space-y-4">
            {/* Admin Button */}
            <button
              onClick={() => handleLogin("admin")}
              className="w-full flex items-center gap-4 p-5 bg-gray-800/50 border border-gray-700 rounded-xl hover:border-blue-500 hover:bg-blue-500/10 transition-all group cursor-pointer"
            >
              <div className="w-14 h-14 rounded-xl bg-blue-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                👑
              </div>
              <div className="text-left flex-1">
                <div className="font-semibold text-white text-lg">Admin</div>
                <div className="text-sm text-gray-500">
                  To'liq boshqaruv — agentlar, modellar, xarajatlar, tasdiqlashlar
                </div>
              </div>
              <div className="text-gray-600 group-hover:text-blue-400 transition-colors">
                →
              </div>
            </button>

            {/* Customer Button */}
            <button
              onClick={() => handleLogin("customer")}
              className="w-full flex items-center gap-4 p-5 bg-gray-800/50 border border-gray-700 rounded-xl hover:border-green-500 hover:bg-green-500/10 transition-all group cursor-pointer"
            >
              <div className="w-14 h-14 rounded-xl bg-green-600 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                💬
              </div>
              <div className="text-left flex-1">
                <div className="font-semibold text-white text-lg">Mijoz</div>
                <div className="text-sm text-gray-500">
                  AI chat, hujjatlar, bilim bazasi — oddiy foydalanuvchi
                </div>
              </div>
              <div className="text-gray-600 group-hover:text-green-400 transition-colors">
                →
              </div>
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-gray-600 text-xs mt-6">
          Nexora AI v1.0 — Demo kirish
        </p>
      </div>
    </div>
  );
}
