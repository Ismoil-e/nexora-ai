"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export type UserRole = "admin" | "customer";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  login: (role: UserRole) => void;
  logout: () => void;
  isAdmin: boolean;
  isCustomer: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: () => {},
  isAdmin: false,
  isCustomer: false,
});

export function useAuth() {
  return useContext(AuthContext);
}

const DEMO_USERS: Record<UserRole, AuthUser> = {
  admin: {
    id: "admin-001",
    name: "Ismoil Admin",
    email: "admin@nexora.ai",
    role: "admin",
  },
  customer: {
    id: "cust-001",
    name: "Mijoz Test",
    email: "mijoz@nexora.ai",
    role: "customer",
  },
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("nexora_user");
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {}
    }
  }, []);

  const login = (role: UserRole) => {
    const u = DEMO_USERS[role];
    setUser(u);
    localStorage.setItem("nexora_user", JSON.stringify(u));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("nexora_user");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        isAdmin: user?.role === "admin",
        isCustomer: user?.role === "customer",
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
