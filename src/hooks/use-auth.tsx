'use client';

import { createContext, useContext, useState, type ReactNode } from 'react';

type AuthContextType = {
  isAuthenticated: boolean;
  userId: string | null;
  isAdmin: boolean;
  login: () => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  const login = () => {
    setIsAuthenticated(true);
    // For this demo, we'll hardcode the admin user ID
    const mockUserId = 'mock-user-123';
    setUserId(mockUserId);
    setIsAdmin(true); // Treat this user as admin
  };
  
  const logout = () => {
    setIsAuthenticated(false);
    setUserId(null);
    setIsAdmin(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, userId, isAdmin, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
