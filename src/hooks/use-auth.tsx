'use client';

import { SessionProvider, useSession, signIn, signOut } from 'next-auth/react';
import * as React from 'react';

type AuthContextType = {
  isAuthenticated: boolean;
  userId: string | null;
  isAdmin: boolean;
  login: () => void;
  logout: () => void;
};

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

function AuthProviderContent({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  
  const isAuthenticated = status === 'authenticated';
  
  // In a real app, you might get this from the session token
  const isAdmin = isAuthenticated && session?.user?.email === 'admin@ufl.edu';
  const userId = session?.user?.id ?? null;

  const login = () => signIn('gatorlink');
  const logout = () => signOut();

  return (
    <AuthContext.Provider value={{ isAuthenticated, userId, isAdmin, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AuthProviderContent>{children}</AuthProviderContent>
    </SessionProvider>
  )
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
