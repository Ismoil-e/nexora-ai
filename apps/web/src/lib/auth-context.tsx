"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface UserProfile {
  id: string;
  firstName: string;
  lastName: string;
  name: string; // firstName + lastName
  businessName: string;
  email: string;
  balance: string;
  photoData?: string;
  role: "admin" | "customer";
}

interface AuthContextType {
  user: UserProfile | null;
  isLoggedIn: boolean;
  isAdmin: boolean;
  isCustomer: boolean;
  login: (email?: string, password?: string) => Promise<boolean>;
  register: (data: {
    firstName: string;
    lastName: string;
    businessName: string;
    email: string;
    password?: string;
  }) => Promise<boolean>;
  logout: () => void;
  updateProfile: (data: Partial<UserProfile>) => void;
}

const DEFAULT_PROFILE: UserProfile = {
  id: "user-default-1",
  firstName: "Ismoil",
  lastName: "Rahmonaliyev",
  name: "Ismoil Rahmonaliyev",
  businessName: "Nexora Business",
  email: "ismoil@nexora.ai",
  balance: "50,000 UZS",
  role: "admin",
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoggedIn: false,
  isAdmin: true,
  isCustomer: false,
  login: async () => true,
  register: async () => true,
  logout: () => {},
  updateProfile: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("userProfile");
      const loggedInFlag = localStorage.getItem("isLoggedIn") === "true";
      if (stored && loggedInFlag) {
        const parsed = JSON.parse(stored);
        setUser({
          ...DEFAULT_PROFILE,
          ...parsed,
          name: `${parsed.firstName || ""} ${parsed.lastName || ""}`.trim() || DEFAULT_PROFILE.name,
        });
        setIsLoggedIn(true);
      } else {
        // Agar birinchi marta kirgan bo'lsa, avtomatik ravishda default profilni faollashtiramiz
        setUser(DEFAULT_PROFILE);
        setIsLoggedIn(true);
        localStorage.setItem("userProfile", JSON.stringify(DEFAULT_PROFILE));
        localStorage.setItem("isLoggedIn", "true");
      }
    } catch {
      setUser(DEFAULT_PROFILE);
      setIsLoggedIn(true);
    }
  }, []);

  const login = async (email?: string) => {
    const current = user || DEFAULT_PROFILE;
    const updated: UserProfile = {
      ...current,
      email: email || current.email,
    };
    setUser(updated);
    setIsLoggedIn(true);
    localStorage.setItem("userProfile", JSON.stringify(updated));
    localStorage.setItem("isLoggedIn", "true");
    return true;
  };

  const register = async (data: {
    firstName: string;
    lastName: string;
    businessName: string;
    email: string;
    password?: string;
  }) => {
    const newProfile: UserProfile = {
      id: `user-${Date.now()}`,
      firstName: data.firstName,
      lastName: data.lastName,
      name: `${data.firstName} ${data.lastName}`.trim(),
      businessName: data.businessName,
      email: data.email,
      balance: "50,000 UZS",
      role: "customer",
    };
    setUser(newProfile);
    setIsLoggedIn(true);
    localStorage.setItem("userProfile", JSON.stringify(newProfile));
    localStorage.setItem("isLoggedIn", "true");
    return true;
  };

  const logout = () => {
    setIsLoggedIn(false);
    setUser(null);
    localStorage.setItem("isLoggedIn", "false");
    localStorage.removeItem("userProfile");
  };

  const updateProfile = (data: Partial<UserProfile>) => {
    setUser((prev) => {
      const base = prev || DEFAULT_PROFILE;
      const updated = { ...base, ...data };
      if (data.firstName || data.lastName) {
        updated.name = `${updated.firstName} ${updated.lastName}`.trim();
      }
      localStorage.setItem("userProfile", JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        isAdmin: user?.role === "admin",
        isCustomer: user?.role === "customer",
        login,
        register,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
