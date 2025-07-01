'use client';

import * as React from 'react';

type AuthContextType = {
  isAuthenticated: boolean;
  userId: string | null;
  isAdmin: boolean;
  login: () => void;
  logout: () => void;
};

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  const [userId, setUserId] = React.useState<string | null>(null);
  const [isAdmin, setIsAdmin] = React.useState(false);

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
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
