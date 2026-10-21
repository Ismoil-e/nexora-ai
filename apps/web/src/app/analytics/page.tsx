"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export default function AnalyticsPage() {
  const { user } = useAuth();
  const [period, setPeriod] = useState<"7d" | "30d" | "90d">("30d");

  const MONTHS_DATA = [
    { label: "May", revenue: 98, profit: 26 },
    { label: "Iyun", revenue: 112, profit: 31 },
    { label: "Iyul", revenue: 125, profit: 34 },
    { label: "Avg", revenue: 138, profit: 39 },
    { label: "Sen", revenue: 142, profit: 40 },
    { label: "Okt", revenue: 156, profit: 45 },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col selection:bg-purple-600/40">
      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#070b14]/85 border-b border-[#8da9ff]/15 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="text-xs font-semibold text-gray-400 hover:text-white transition-colors flex items-center gap-1.5"
          >
            <span>←</span>
            <span>Chatga qaytish</span>
          </Link>
          <div className="w-px h-4 bg-gray-800" />
          <div className="text-lg font-black tracking-tight flex items-center gap-1">
            <span className="text-white">Nexora</span>
            <span className="text-gradient">AI</span>
            <span className="ml-2 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-cyan-900/40 text-cyan-400 border border-cyan-800/40">
              BI & Analitika
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {(["7d", "30d", "90d"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                period === p
                  ? "btn-gradient shadow-md"
                  : "bg-gray-900 text-gray-400 hover:text-white border border-gray-800"
              }`}
            >
              {p === "7d" ? "7 kun" : p === "30d" ? "30 kun" : "3 oy"}
            </button>
          ))}
        </div>
      </header>

      <div className="max-w-6xl mx-auto w-full p-6 sm:p-8 flex-1">
        {/* Title */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black text-white">Biznes Intellekti & KPI Paneli</h1>
            <p className="text-xs text-gray-400 mt-1">
              Savdo tushumi, rentabellik va AI tomonidan prognoz qilingan tavsiyalar
            </p>
          </div>
          <Link
            href="/chat"
            className="px-4 py-2 rounded-xl btn-gradient text-xs font-bold shadow-md"
          >
            AI Tahlilchi bilan suhbat 🤖
          </Link>
        </div>

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="glass-card glass-card-hover rounded-2xl p-5 border border-[#8da9ff]/15">
            <div className="flex items-center justify-between text-xs text-gray-400 font-medium">
              <span>Umumiy tushum</span>
              <span className="text-green-400 font-bold bg-green-950/60 px-2 py-0.5 rounded border border-green-800/40">
                +18.4%
              </span>
            </div>
            <div className="text-2xl font-black text-white mt-2">156.4 mln UZS</div>
            <div className="text-[11px] text-gray-500 mt-1">O'tgan davr: 132.1 mln UZS</div>
          </div>

          <div className="glass-card glass-card-hover rounded-2xl p-5 border border-[#8da9ff]/15">
            <div className="flex items-center justify-between text-xs text-gray-400 font-medium">
              <span>Sof foyda</span>
              <span className="text-cyan-400 font-bold bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                28.8% marja
              </span>
            </div>
            <div className="text-2xl font-black text-cyan-400 mt-2">45.1 mln UZS</div>
            <div className="text-[11px] text-gray-500 mt-1">Reja: 40 mln UZS (112%)</div>
          </div>

          <div className="glass-card glass-card-hover rounded-2xl p-5 border border-[#8da9ff]/15">
            <div className="flex items-center justify-between text-xs text-gray-400 font-medium">
              <span>Faol mijozlar</span>
              <span className="text-purple-400 font-bold bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">
                +140 yangi
              </span>
            </div>
            <div className="text-2xl font-black text-purple-400 mt-2">1,280 ta</div>
            <div className="text-[11px] text-gray-500 mt-1">Takroriy xarid: 64%</div>
          </div>

          <div className="glass-card glass-card-hover rounded-2xl p-5 border border-[#8da9ff]/15">
            <div className="flex items-center justify-between text-xs text-gray-400 font-medium">
              <span>O'rtacha chek</span>
              <span className="text-green-400 font-bold bg-green-950/60 px-2 py-0.5 rounded border border-green-800/40">
                +6.2%
              </span>
            </div>
            <div className="text-2xl font-black text-white mt-2">395,000 UZS</div>
            <div className="text-[11px] text-gray-500 mt-1">Konversiya ko'rsatkichi: 4.8%</div>
          </div>
        </div>

        {/* Charts & AI Insights Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
          {/* Revenue Chart Visualizer */}
          <div className="lg:col-span-8 glass-card rounded-2xl p-6 border border-[#8da9ff]/15 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-sm font-bold text-white">Oylik daromad va foyda dinamikasi</h2>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  Oxirgi 6 oylik solishtirma diagramma (mln UZS)
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1.5 text-cyan-400">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Tushum
                </span>
                <span className="flex items-center gap-1.5 text-purple-400">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-400" /> Sof foyda
                </span>
              </div>
            </div>

            {/* Custom Bar Graph */}
            <div className="h-64 flex items-end justify-between gap-4 pt-6 pb-2 border-b border-gray-800">
              {MONTHS_DATA.map((item, idx) => (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                  <div className="w-full flex items-end justify-center gap-1.5 h-full">
                    {/* Revenue Bar */}
                    <div
                      style={{ height: `${(item.revenue / 170) * 100}%` }}
                      className="w-1/2 max-w-[28px] rounded-t-lg bg-gradient-to-t from-cyan-600/40 to-cyan-400 hover:brightness-125 transition-all relative group-hover:shadow-[0_0_15px_rgba(34,211,238,0.5)]"
                    >
                      <span className="absolute -top-7 left-1/2 -translate-x-1/2 text-[10px] font-bold text-cyan-300 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-gray-900 px-1.5 py-0.5 rounded border border-cyan-500/30">
                        {item.revenue}M
                      </span>
                    </div>

                    {/* Profit Bar */}
                    <div
                      style={{ height: `${(item.profit / 170) * 100}%` }}
                      className="w-1/2 max-w-[28px] rounded-t-lg bg-gradient-to-t from-purple-600/40 to-purple-400 hover:brightness-125 transition-all relative group-hover:shadow-[0_0_15px_rgba(139,92,246,0.5)]"
                    >
                      <span className="absolute -top-7 left-1/2 -translate-x-1/2 text-[10px] font-bold text-purple-300 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-gray-900 px-1.5 py-0.5 rounded border border-purple-500/30">
                        {item.profit}M
                      </span>
                    </div>
                  </div>
                  <span className="text-[11px] font-semibold text-gray-400 mt-2">{item.label}</span>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between text-[11px] text-gray-500 pt-4">
              <span>Minimal: 98 mln UZS</span>
              <span className="text-cyan-400 font-semibold">O'sish tendensiyasi: Barqaror (+24%)</span>
              <span>Maksimal: 156 mln UZS</span>
            </div>
          </div>

          {/* AI Causal Insights & Anomalies */}
          <div className="lg:col-span-4 glass-card rounded-2xl p-6 border border-purple-500/25 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xl">🧠</span>
                <div>
                  <h3 className="text-sm font-bold text-white">AI Biznes Xulosalari</h3>
                  <p className="text-[10px] text-gray-400">Avtomatik anomaliya va tavsiyalar</p>
                </div>
              </div>

              <div className="space-y-3.5 text-xs">
                <div className="p-3.5 rounded-xl bg-purple-950/30 border border-purple-800/40">
                  <div className="font-bold text-purple-300 mb-1 flex items-center gap-1.5">
                    <span>💡 Savdo o'sishi</span>
                  </div>
                  <p className="text-gray-300 leading-relaxed text-[11px]">
                    Oxirgi 2 haftada Q3 toifasidagi xizmatlarga talab 34% oshdi. Asosiy mijoz oqimi Instagram orqali kelmoqda.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-800/40">
                  <div className="font-bold text-amber-300 mb-1 flex items-center gap-1.5">
                    <span>⚠️ Xarajat nazorati</span>
                  </div>
                  <p className="text-gray-300 leading-relaxed text-[11px]">
                    Logistika va yetkazib berish xarajatlari 8.2% ga qimmatlashgan. Shartnomalarni qayta ko'rish tavsiya etiladi.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-cyan-950/30 border border-cyan-800/40">
                  <div className="font-bold text-cyan-300 mb-1 flex items-center gap-1.5">
                    <span>🚀 O'sish nuqtasi</span>
                  </div>
                  <p className="text-gray-300 leading-relaxed text-[11px]">
                    Mavjud mijozlarga takroriy sotuv (cross-sell) oqimini yoqish orqali daromadni 15% ga oshirish mumkin.
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-800 mt-4">
              <Link
                href="/chat"
                className="w-full py-2.5 rounded-xl bg-gray-900 border border-gray-800 hover:border-purple-500/40 text-white text-xs font-bold text-center block transition-colors"
              >
                AI dan batafsil hisobot so'rash →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
