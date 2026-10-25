"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  loginRequest,
  registerRequest,
  revokeAuthSession,
  verifyMfaRequest,
} from "@/lib/api";

export interface UserProfile {
  id: string;
  firstName: string;
  lastName: string;
  name: string;
  businessName: string;
  email: string;
  balance: string;
  photoData?: string;
  role: "admin" | "customer";
}

interface AuthContextType {
  user: UserProfile | null;
  isLoggedIn: boolean;
  isLoading: boolean;
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
  verifyMfaLogin: (code: string) => Promise<boolean>;
  logout: () => void;
  updateProfile: (data: Partial<UserProfile>) => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoggedIn: false,
  isLoading: true,
  isAdmin: false,
  isCustomer: false,
  login: async () => false,
  register: async () => false,
  verifyMfaLogin: async () => false,
  logout: () => {},
  updateProfile: () => {},
});

function profileFromApi(apiUser: Record<string, any>): UserProfile {
  let previous: Partial<UserProfile> = {};
  try {
    const saved = localStorage.getItem("userProfile");
    if (saved) previous = JSON.parse(saved);
  } catch {}

  const firstName = apiUser.first_name || previous.firstName || "";
  const lastName = apiUser.last_name || previous.lastName || "";
  return {
    id: String(apiUser.id),
    firstName,
    lastName,
    name: [firstName, lastName].filter(Boolean).join(" "),
    businessName: apiUser.company_name || previous.businessName || "Biznesim",
    email: apiUser.email,
    balance: previous.balance || "0 UZS",
    photoData: apiUser.avatar_url || undefined,
    role: apiUser.role === "admin" ? "admin" : "customer",
  };
}

function saveSession(accessToken: string, refreshToken: string, apiUser: Record<string, any>) {
  const profile = profileFromApi(apiUser);
  localStorage.setItem("token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
  localStorage.setItem("userProfile", JSON.stringify(profile));
  localStorage.setItem("isLoggedIn", "true");
  return profile;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingMfaUserId, setPendingMfaUserId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const token = localStorage.getItem("token");
      const stored = localStorage.getItem("userProfile");
      if (token && stored) {
        setUser(JSON.parse(stored));
        setIsLoggedIn(true);
      } else {
        setUser(null);
        setIsLoggedIn(false);
      }
    } catch {
      setUser(null);
      setIsLoggedIn(false);
    } finally {
      setIsLoading(false);
    }

    const expireSession = () => {
      setUser(null);
      setIsLoggedIn(false);
      localStorage.setItem("isLoggedIn", "false");
    };
    window.addEventListener("nexora:auth-expired", expireSession);
    return () => window.removeEventListener("nexora:auth-expired", expireSession);
  }, []);

  const login = async (email?: string, password?: string) => {
    if (!email || !password) throw new Error("Email va parolni kiriting.");
    const result = await loginRequest(email, password);
    if (result.requires_mfa) {
      setPendingMfaUserId(String(result.user.id));
      throw new Error("MFA_REQUIRED");
    }

    const profile = saveSession(result.access_token, result.refresh_token, result.user);
    setUser(profile);
    setIsLoggedIn(true);
    setPendingMfaUserId(null);
    return true;
  };

  const register = async (data: {
    firstName: string;
    lastName: string;
    businessName: string;
    email: string;
    password?: string;
  }) => {
    if (!data.password) throw new Error("Parolni kiriting.");
    const result = await registerRequest({
      first_name: data.firstName,
      last_name: data.lastName,
      company_name: data.businessName,
      email: data.email,
      password: data.password,
    });
    const profile = saveSession(result.access_token, result.refresh_token, result.user);
    setUser(profile);
    setIsLoggedIn(true);
    return true;
  };

  const verifyMfaLogin = async (code: string) => {
    if (!pendingMfaUserId) throw new Error("Avval tizimga kiring.");
    const result = await verifyMfaRequest(pendingMfaUserId, code);
    const profile = saveSession(result.access_token, result.refresh_token, result.user);
    setUser(profile);
    setIsLoggedIn(true);
    setPendingMfaUserId(null);
    return true;
  };

  const logout = () => {
    void revokeAuthSession().catch(() => {});
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("userProfile");
    localStorage.setItem("isLoggedIn", "false");
    setUser(null);
    setIsLoggedIn(false);
  };

  const updateProfile = (data: Partial<UserProfile>) => {
    setUser((previous) => {
      if (!previous) return previous;
      const updated = { ...previous, ...data };
      if (data.firstName || data.lastName) {
        updated.name = [updated.firstName, updated.lastName].filter(Boolean).join(" ");
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
        isLoading,
        isAdmin: user?.role === "admin",
        isCustomer: user?.role === "customer",
        login,
        register,
        verifyMfaLogin,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}