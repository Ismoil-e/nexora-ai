"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function HomePage() {
  const { isLoggedIn, user } = useAuth();

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col selection:bg-purple-600/40">
      {/* Landing Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#070b14]/80 border-b border-[#8da9ff]/15 px-6 lg:px-16 py-4 flex items-center justify-between">
        <Link href="/" className="text-2xl font-black tracking-tight flex items-center gap-1.5">
          <span className="text-white">Nexora</span>
          <span className="text-gradient font-extrabold">AI</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-400">
          <a href="#about" className="hover:text-white transition-colors">
            About us
          </a>
          <a href="#features" className="hover:text-white transition-colors">
            Imkoniyatlar
          </a>
          <a href="#partners" className="hover:text-white transition-colors">
            Hamkorlar
          </a>
        </nav>

        <div className="flex items-center gap-3">
          {isLoggedIn && user ? (
            <Link
              href="/chat"
              className="px-5 py-2.5 rounded-xl btn-gradient text-sm font-bold shadow-lg"
            >
              Chatni ochish →
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors font-medium"
              >
                Login
              </Link>
              <Link
                href="/chat"
                className="px-5 py-2.5 rounded-xl btn-gradient text-sm font-bold shadow-lg"
              >
                Chatni ochish
              </Link>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-12 py-12 lg:py-20">
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center mb-28">
          {/* Left Copy */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-900/30 border border-purple-500/30 text-xs font-semibold text-purple-300 uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              Bizneslar uchun AI
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-[1.15]">
              Biznesingiz uchun <br />
              <span className="text-gradient">sodda AI yordamchi.</span>
            </h1>

            <p className="text-gray-400 text-base sm:text-lg leading-relaxed max-w-xl">
              Nexora AI bizneslar uchun yaratilgan chat-markazli platforma. Asosiy maqsad:
              foydalanuvchi tez kiradi, savol beradi va kerakli javobni ortiqcha bosqichlarsiz oladi.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                href="/chat"
                className="px-8 py-3.5 rounded-xl btn-gradient text-sm font-bold shadow-xl flex items-center gap-2"
              >
                <span>Platformaga kirish</span>
                <span>→</span>
              </Link>
              <a
                href="#about"
                className="px-6 py-3.5 rounded-xl bg-gray-900/90 border border-gray-800 text-gray-300 hover:text-white hover:border-gray-700 text-sm font-semibold transition-all"
              >
                Ko'proq bilish
              </a>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 pt-6 border-t border-gray-800/80">
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-white">24/7</div>
                <div className="text-xs text-gray-500 mt-1 font-medium">AI yordam</div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-cyan-400">2-3</div>
                <div className="text-xs text-gray-500 mt-1 font-medium">klikda kirish</div>
              </div>
              <div>
                <div className="text-2xl sm:text-3xl font-extrabold text-purple-400">100%</div>
                <div className="text-xs text-gray-500 mt-1 font-medium">responsive</div>
              </div>
            </div>
          </div>

          {/* Right Hero Panel / Overview Cards */}
          <div className="lg:col-span-5 space-y-4">
            <div className="glass-card glass-card-hover rounded-2xl p-7 relative overflow-hidden glow-box">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/10 rounded-full blur-2xl pointer-events-none" />
              <div className="text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-2">
                Nexora overview
              </div>
              <h2 className="text-xl font-bold text-white mb-4 leading-snug">
                Login, profil va AI chat bitta qulay oqimda ishlaydi.
              </h2>
              <ul className="space-y-3 text-sm text-gray-300">
                <li className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-purple-900/50 text-purple-300 flex items-center justify-center text-xs">
                    ✓
                  </span>
                  Minimalistik va tez interfeys
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-purple-900/50 text-purple-300 flex items-center justify-center text-xs">
                    ✓
                  </span>
                  Chat asosiy boshqaruv nuqtasi
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-purple-900/50 text-purple-300 flex items-center justify-center text-xs">
                    ✓
                  </span>
                  Desktop va mobile uchun mos
                </li>
              </ul>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6 border-purple-500/20">
              <div className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-1">
                About us
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">
                Biz murakkab AI jarayonlarini oddiy, tez va tushunarli interfeysga aylantiramiz.
              </p>
            </div>
          </div>
        </section>

        {/* Section: About Us */}
        <section id="about" className="py-16 border-t border-gray-800/60">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2">
              About us
            </p>
            <h2 className="text-3xl font-extrabold text-white">
              Nexora AI nima taklif qiladi?
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card glass-card-hover rounded-2xl p-6">
              <div className="w-12 h-12 rounded-xl bg-purple-900/40 text-purple-300 flex items-center justify-center text-xl mb-4 border border-purple-800/40">
                💬
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Chat asosidagi boshqaruv</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Platformadagi asosiy ishlash logikasi bitta oynada, chat orqali quriladi.
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6">
              <div className="w-12 h-12 rounded-xl bg-cyan-900/40 text-cyan-300 flex items-center justify-center text-xl mb-4 border border-cyan-800/40">
                ⚡
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Tez va tushunarli UX</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Foydalanuvchi login qiladi, chatga kiradi va darhol ishni boshlaydi.
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6">
              <div className="w-12 h-12 rounded-xl bg-blue-900/40 text-blue-300 flex items-center justify-center text-xl mb-4 border border-blue-800/40">
                ✨
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Minimalistik dizayn</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Ortiqcha elementlarsiz, sodda va zamonaviy ko‘rinish tez ishlashga yordam beradi.
              </p>
            </div>
          </div>
        </section>

        {/* Section: Features */}
        <section id="features" className="py-16 border-t border-gray-800/60">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <p className="text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-2">
              Imkoniyatlar
            </p>
            <h2 className="text-3xl font-extrabold text-white">
              Asosiy imkoniyatlar
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card glass-card-hover rounded-2xl p-6 relative">
              <span className="text-xs font-mono font-bold text-gray-500 mb-2 block">
                01
              </span>
              <h3 className="text-lg font-bold text-white mb-2">💬 Markaziy AI Chat</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Foydalanuvchi xabarlari o‘ngda, AI javoblari chapda ko‘rinadigan tez va qulay chat interfeysi.
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6 relative">
              <span className="text-xs font-mono font-bold text-gray-500 mb-2 block">
                02
              </span>
              <h3 className="text-lg font-bold text-white mb-2">🤖 Mutaxassis AI Agentlar</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Moliya, Savdo tahlili, HR va Hujjatlar bo'yicha maxsus o'rgatilgan ixtisoslashgan agentlar.
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6 relative">
              <span className="text-xs font-mono font-bold text-gray-500 mb-2 block">
                03
              </span>
              <h3 className="text-lg font-bold text-white mb-2">📄 Hujjatlar Razvedkasi</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                PDF, Word, Excel hisobotlarni yuklang — AI ularni to'liq o'qiydi va aniq javob beradi (RAG).
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6 relative">
              <span className="text-xs font-mono font-bold text-gray-500 mb-2 block">
                04
              </span>
              <h3 className="text-lg font-bold text-white mb-2">📊 BI & Savdo Analitikasi</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Oylik tushum, sof foyda, mijozlar o'sishi va avtomatik anomaliyalarni aniqlash paneli.
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6 relative">
              <span className="text-xs font-mono font-bold text-gray-500 mb-2 block">
                05
              </span>
              <h3 className="text-lg font-bold text-white mb-2">📚 Kompaniya Bilim Bazasi</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Ichki tartib-qoidalar, xizmatlar va mahsulotlar bo'yicha yagona semantik vektor qidiruvi.
              </p>
            </div>

            <div className="glass-card glass-card-hover rounded-2xl p-6 relative">
              <span className="text-xs font-mono font-bold text-gray-500 mb-2 block">
                06
              </span>
              <h3 className="text-lg font-bold text-white mb-2">📱 100% Responsive & Xavfsiz</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Kompyuter, planshet va smartfonlarda qulay ishlaydi, ma'lumotlar to'liq himoyalangan.
              </p>
            </div>
          </div>
        </section>

        {/* Section: Partners */}
        <section id="partners" className="py-16 border-t border-gray-800/60">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2">
              Hamkorlar
            </p>
            <h2 className="text-3xl font-extrabold text-white">
              Qaysi yo'nalishlar uchun mos
            </h2>
          </div>

          <div className="flex flex-wrap justify-center gap-3 max-w-3xl mx-auto">
            {[
              "Startup jamoalar",
              "Xizmat ko'rsatuvchi bizneslar",
              "Konsalting loyihalar",
              "Ta'lim platformalari",
              "Savdo va servis",
              "Raqamli agentliklar",
            ].map((chip) => (
              <div
                key={chip}
                className="px-5 py-2.5 rounded-full bg-gray-900/90 border border-gray-800 text-gray-300 text-sm font-medium hover:border-purple-500/50 hover:text-white transition-all cursor-default"
              >
                {chip}
              </div>
            ))}
          </div>
        </section>

        {/* Section: CTA */}
        <section className="mt-12 p-8 sm:p-12 rounded-3xl bg-gradient-to-r from-purple-900/30 via-indigo-900/20 to-cyan-900/30 border border-purple-500/30 flex flex-col md:flex-row items-center justify-between gap-8 glow-box">
          <div>
            <p className="text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-2">
              Ready to start?
            </p>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
              Nexora AI bilan ishni tez va sodda boshlang.
            </h2>
          </div>
          <div className="flex flex-wrap gap-4">
            <Link
              href="/login"
              className="px-6 py-3 rounded-xl btn-gradient text-sm font-bold shadow-lg"
            >
              Account ochish
            </Link>
            <Link
              href="/chat"
              className="px-6 py-3 rounded-xl bg-gray-900/90 border border-gray-700 text-white hover:border-gray-500 text-sm font-semibold transition-colors"
            >
              Chatga o'tish
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/80 px-6 py-8 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <span className="text-white font-bold">Nexora</span>{" "}
            <span className="text-cyan-400 font-bold">AI</span> — Bizneslar uchun sodda AI yordamchi
          </div>
          <div>© {new Date().getFullYear()} Nexora AI. Barcha huquqlar himoyalangan.</div>
        </div>
      </footer>
    </div>
  );
}
