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
    // In a real Shibboleth integration, this function would initiate a redirect
    // to the University's Identity Provider (IdP).
    // Example: window.location.href = 'https://login.ufl.edu/idp/profile/SAML2/Redirect/SSO?execution=e1s1';
    
    // For this dummy implementation, we will simulate a successful login
    // immediately. We'll set a mock user ID as if the user has returned
    // from the IdP with valid authentication assertions.
    
    setIsAuthenticated(true);
    const mockUserId = 'gator-user-123'; // A mock user ID for the demo
    setUserId(mockUserId);
    // In a real app, admin status would be determined from the Shibboleth
    // assertions (e.g., group membership). Here, we'll keep the mock admin status.
    setIsAdmin(true);
  };
  
  const logout = () => {
    // In a real Shibboleth integration, this would redirect to a logout URL
    // to terminate the IdP session.
    // Example: window.location.href = '/Shibboleth.sso/Logout';

    // For this dummy implementation, we just clear the local state.
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
