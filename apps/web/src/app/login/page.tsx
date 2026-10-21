"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register form state
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail.trim()) return;

    await login(loginEmail, loginPassword);
    router.push("/chat");
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName.trim() || !regEmail.trim()) return;

    await register({
      firstName,
      lastName,
      businessName: businessName || "Mening Biznesim",
      email: regEmail,
      password: regPassword,
    });
    router.push("/chat");
  };

  const handleGoogleLogin = async () => {
    await login("google.user@gmail.com");
    router.push("/chat");
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col items-center justify-center p-4 selection:bg-purple-600/40">
      {/* Brand */}
      <div className="text-center mb-8">
        <Link href="/" className="text-3xl font-black tracking-tight inline-flex items-center gap-1.5">
          <span className="text-white">Nexora</span>
          <span className="text-gradient">AI</span>
        </Link>
        <p className="text-xs text-gray-500 mt-1">Biznesingiz uchun sodda AI yordamchi</p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md glass-card rounded-3xl p-8 border border-[#8da9ff]/20 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/10 rounded-full blur-2xl pointer-events-none" />

        <h1 className="text-2xl font-black text-center text-white mb-2">
          {isRegisterMode ? "Ro'yxatdan o'tish" : "Tizimga kirish"}
        </h1>
        <p className="text-xs text-center text-gray-400 mb-6">
          {isRegisterMode
            ? "Yangi hisob oching va AI yordamchi bilan ishni boshlang"
            : "Platformaga kirish uchun ma'lumotlaringizni kiriting"}
        </p>

        {!isRegisterMode ? (
          /* Login Form */
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Email</label>
              <input
                type="email"
                required
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="Email manzilingizni kiriting"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors placeholder:text-gray-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Parol</label>
              <input
                type="password"
                required
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Parolni kiriting"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors placeholder:text-gray-600"
              />
            </div>

            <button
              type="submit"
              className="w-full py-3.5 rounded-xl btn-gradient text-sm font-bold shadow-xl mt-2 cursor-pointer"
            >
              Kirish
            </button>
          </form>
        ) : (
          /* Register Form */
          <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Ism</label>
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Ismingiz"
                  className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Familiya</label>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Familiyangiz"
                  className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">Biznes nomi</label>
              <input
                type="text"
                required
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="Masalan: Start Market"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">Email</label>
              <input
                type="email"
                required
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="Email manzilingiz"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">Parol</label>
              <input
                type="password"
                required
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="Parolni kiriting"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              type="submit"
              className="w-full py-3.5 rounded-xl btn-gradient text-sm font-bold shadow-xl mt-2 cursor-pointer"
            >
              Ro'yxatdan o'tish
            </button>
          </form>
        )}

        {/* Divider */}
        <div className="relative my-6 flex items-center justify-center">
          <div className="border-t border-gray-800 w-full" />
          <span className="bg-[#0b1222] px-3 text-xs text-gray-500 uppercase tracking-wider relative">
            yoki
          </span>
        </div>

        {/* Google Sign-in */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          className="w-full py-3 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 text-white text-xs font-bold transition-all flex items-center justify-center gap-3 cursor-pointer"
        >
          <svg width="18" height="18" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Google orqali kirish
        </button>

        {/* Switch mode */}
        <div className="mt-6 text-center text-xs text-gray-400">
          {!isRegisterMode ? (
            <>
              Accountingiz yo'qmi?{" "}
              <button
                type="button"
                onClick={() => setIsRegisterMode(true)}
                className="text-cyan-400 hover:text-cyan-300 font-semibold cursor-pointer underline ml-1"
              >
                Ro'yxatdan o'tish
              </button>
            </>
          ) : (
            <>
              Profilingiz bormi?{" "}
              <button
                type="button"
                onClick={() => setIsRegisterMode(false)}
                className="text-cyan-400 hover:text-cyan-300 font-semibold cursor-pointer underline ml-1"
              >
                Tizimga kirish
              </button>
            </>
          )}
        </div>

        {/* Back link */}
        <div className="mt-4 text-center">
          <Link href="/" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
            ← Bosh sahifaga qaytish
          </Link>
        </div>
      </div>
    </div>
  );
}
