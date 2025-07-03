'use client';

import { useAuth } from '@/hooks/use-auth';
import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import {
  SidebarProvider,
} from '@/components/ui/sidebar';
import { SettingsSidebar } from '@/components/settings-sidebar';
import { Button } from '@/components/ui/button';
import { UserCircle } from 'lucide-react';
import * as React from 'react';

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, login } = useAuth();

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full bg-background">
        <SettingsSidebar />
        <div className="flex flex-1 flex-col overflow-hidden bg-muted">
          <AppHeader isPaneHeader={true} />

          <main className="flex-1 overflow-y-auto">
            {isAuthenticated ? (
              <div className="p-6 sm:p-8 md:p-10">{children}</div>
            ) : (
              <div className="flex h-full items-center justify-center p-6 text-center">
                <div className="flex max-w-md flex-col items-center rounded-lg border-2 border-dashed bg-card p-6 sm:p-8 lg:p-12">
                  <UserCircle className="h-12 w-12 text-muted-foreground sm:h-16 sm:w-16" />
                  <h2 className="mt-6 text-xl font-semibold tracking-tight sm:text-2xl">Access Your Settings</h2>
                  <p className="mt-2 text-muted-foreground">
                    Sign in with your GatorLink to manage your profile, appearance, and account settings.
                  </p>
                  <Button onClick={login} className="mt-6">
                    Sign In with GatorLink
                  </Button>
                </div>
              </div>
            )}
          </main>

          <AppFooter />
        </div>
      </div>
    </SidebarProvider>
  );
}
