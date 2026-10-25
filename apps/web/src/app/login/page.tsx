"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, register, verifyMfaLogin } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [requiresMfa, setRequiresMfa] = useState(false);
  const [mfaCode, setMfaCode] = useState("");
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
    setFormError("");
    setIsSubmitting(true);
    try {
      if (requiresMfa) await verifyMfaLogin(mfaCode);
      else await login(loginEmail, loginPassword);
      router.push("/chat");
    } catch (error) {
      if (error instanceof Error && error.message === "MFA_REQUIRED") setRequiresMfa(true);
      else setFormError(error instanceof Error ? error.message : "Kirishda xatolik yuz berdi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    setIsSubmitting(true);
    try {
      await register({
        firstName,
        lastName,
        businessName: businessName || "Mening Biznesim",
        email: regEmail,
        password: regPassword,
      });
      router.push("/chat");
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Ro‘yxatdan o‘tishda xatolik yuz berdi.");
    } finally {
      setIsSubmitting(false);
    }
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
          {requiresMfa ? "Kirishni tasdiqlash" : isRegisterMode ? "Ro'yxatdan o'tish" : "Tizimga kirish"}
        </h1>
        <p className="text-xs text-center text-gray-400 mb-6">
          {requiresMfa
            ? "Tasdiqlash kodini kiriting"
            : isRegisterMode
            ? "Yangi hisob oching va AI yordamchi bilan ishni boshlang"
            : "Platformaga kirish uchun ma'lumotlaringizni kiriting"}
        </p>

        {formError && (
          <div role="alert" className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
            {formError}
          </div>
        )}

        {!isRegisterMode ? (
          /* Login Form */
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            {!requiresMfa ? <>
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

            </> : <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Tasdiqlash kodi</label>
              <input
                type="text"
                inputMode="numeric"
                required
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                placeholder="6 xonali kod"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500"
              />
            </div>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3.5 rounded-xl btn-gradient text-sm font-bold shadow-xl mt-2 cursor-pointer"
            >
              {isSubmitting ? "Kutilmoqda..." : requiresMfa ? "Tasdiqlash" : "Kirish"}
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
                minLength={8}
                pattern="(?=.*[A-Z])(?=.*[0-9]).{8,}"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="Parolni kiriting"
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500"
              />
              <p className="mt-1 text-[10px] text-gray-500">Kamida 8 belgi, 1 ta katta harf va 1 ta raqam.</p>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3.5 rounded-xl btn-gradient text-sm font-bold shadow-xl mt-2 cursor-pointer"
            >
              {isSubmitting ? "Kutilmoqda..." : "Ro'yxatdan o'tish"}
            </button>
          </form>
        )}

        {/* Switch mode */}
        {!requiresMfa && <div className="mt-6 text-center text-xs text-gray-400">
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
        </div>}

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
