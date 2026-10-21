"use client";

import AdminSidebar from "@/components/AdminSidebar";
import { useEffect, useState } from "react";
import { listApprovals, approveAction, rejectAction } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-900/50 text-green-400",
  medium: "bg-yellow-900/50 text-yellow-400",
  high: "bg-orange-900/50 text-orange-400",
  critical: "bg-red-900/50 text-red-400",
};

export default function AdminApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = () => {
    listApprovals().then((d) => setApprovals(d?.items || [])).catch(() => {});
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (id: string) => {
    setLoading(true);
    try { await approveAction(id, "Tasdiqlandi"); refresh(); }
    catch (err: any) { alert(`Xatolik: ${err.message}`); }
    finally { setLoading(false); }
  };

  const handleReject = async (id: string) => {
    const reason = prompt("Rad etish sababi:");
    if (reason === null) return;
    setLoading(true);
    try { await rejectAction(id, reason); refresh(); }
    catch (err: any) { alert(`Xatolik: ${err.message}`); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="ml-64 flex-1 p-8">
        <h1 className="text-2xl font-bold text-white mb-2">✅ Tasdiqlashlar</h1>
        <p className="text-gray-500 mb-6">AI agentlarining hassas amallari uchun inson tasdiqlashi</p>

        {approvals.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
            <div className="text-4xl mb-3">🎉</div>
            <div className="text-gray-400">Tasdiqlash so&apos;rovlari yo&apos;q</div>
          </div>
        ) : (
          <div className="space-y-4">
            {approvals.map((a: any) => (
              <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${RISK_COLORS[a.risk_level] || "bg-gray-800 text-gray-400"}`}>
                        {a.risk_level?.toUpperCase()}
                      </span>
                      <span className="text-sm font-medium text-white">{a.action}</span>
                    </div>
                    <p className="text-sm text-gray-400 mb-2">{a.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-600">
                      <span>🤖 {a.agent_key}</span>
                      <span>⏰ {new Date(a.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button onClick={() => handleApprove(a.id)} disabled={loading}
                      className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm disabled:opacity-50 transition-colors">
                      ✅ Tasdiqlash
                    </button>
                    <button onClick={() => handleReject(a.id)} disabled={loading}
                      className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-800 rounded-lg text-sm disabled:opacity-50 transition-colors">
                      ❌ Rad etish
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
