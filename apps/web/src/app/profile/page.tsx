"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function ProfilePage() {
  const router = useRouter();
  const { user, updateProfile } = useAuth();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [photoData, setPhotoData] = useState<string | undefined>(undefined);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user) {
      setFirstName(user.firstName || "");
      setLastName(user.lastName || "");
      setBusinessName(user.businessName || "");
      setPhotoData(user.photoData);
    }
  }, [user]);

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setPhotoData(event.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfile({
      firstName,
      lastName,
      businessName,
      photoData,
    });
    setSaved(true);
    setTimeout(() => {
      router.push("/chat");
    }, 800);
  };

  const initials = `${firstName?.charAt(0) || "N"}${lastName?.charAt(0) || "A"}`.toUpperCase();

  return (
    <div className="min-h-screen bg-[#070b14] text-[#f0f4ff] flex flex-col selection:bg-purple-600/40">
      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#070b14]/85 border-b border-[#8da9ff]/15 px-6 py-4 flex items-center justify-between">
        <Link
          href="/chat"
          className="text-xs font-semibold text-gray-400 hover:text-white transition-colors flex items-center gap-1.5"
        >
          <span>←</span>
          <span>Chatga qaytish</span>
        </Link>
        <div className="text-xl font-black tracking-tight flex items-center gap-1">
          <span className="text-white">Nexora</span>
          <span className="text-gradient">AI</span>
        </div>
        <div className="w-16" />
      </header>

      {/* Main Form */}
      <main className="flex-1 max-w-xl w-full mx-auto p-6 flex items-center justify-center">
        <div className="w-full glass-card rounded-3xl p-8 border border-[#8da9ff]/20 shadow-2xl relative overflow-hidden">
          <h1 className="text-2xl font-black text-white text-center mb-1">
            Profilni o'zgartirish
          </h1>
          <p className="text-xs text-gray-400 text-center mb-8">
            Rasm, ism, familiya va biznes nomini yangilang
          </p>

          {saved && (
            <div className="mb-6 p-3 rounded-xl bg-green-900/40 border border-green-500/50 text-green-300 text-xs text-center font-medium">
              ✓ Profil ma'lumotlari muvaffaqiyatli saqlandi!
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Photo upload preview */}
            <div className="flex flex-col items-center gap-3 pb-2">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-purple-600 to-cyan-500 text-black font-extrabold text-2xl flex items-center justify-center overflow-hidden shadow-xl border border-white/20">
                {photoData ? (
                  <img src={photoData} alt="Profile photo" className="w-full h-full object-cover" />
                ) : (
                  initials
                )}
              </div>
              <label className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer bg-gray-900/80 border border-gray-800 px-4 py-2 rounded-xl">
                Photo yuklash
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                />
              </label>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">Ism</label>
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">Familiya</label>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                Biznes nomi
              </label>
              <input
                type="text"
                required
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                className="w-full bg-gray-900/90 border border-gray-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>

            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 flex items-center justify-between text-xs">
              <span className="text-gray-400">Joriy hisob balansi:</span>
              <span className="font-bold text-cyan-400">{user?.balance || "50,000 UZS"}</span>
            </div>

            <div className="pt-2 flex items-center gap-3">
              <Link
                href="/chat"
                className="flex-1 py-3.5 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 hover:text-white text-xs font-bold text-center transition-colors"
              >
                Bekor qilish
              </Link>
              <button
                type="submit"
                className="flex-1 py-3.5 rounded-xl btn-gradient text-xs font-bold shadow-xl cursor-pointer"
              >
                Saqlash
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
