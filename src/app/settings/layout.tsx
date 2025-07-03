'use client';

import { useAuth } from '@/hooks/use-auth';
import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import {
  SidebarProvider,
  SidebarTrigger,
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
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* This header is part of the right pane, not fixed globally */}
          <AppHeader isPaneHeader={true} />

          {/* This main area is scrollable and fills the space between header and footer */}
          <main className="flex-1 overflow-y-auto bg-muted">
            {/* Mobile-only header with trigger */}
            <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
              <SidebarTrigger />
              <h1 className="text-lg font-semibold">Settings</h1>
            </header>

            {isAuthenticated ? (
              <div className="p-6 sm:p-8 md:p-10">{children}</div>
            ) : (
              <div className="flex h-full items-center justify-center p-6 text-center">
                <div className="flex max-w-md flex-col items-center rounded-lg border-2 border-dashed bg-muted/50 p-6 sm:p-8 lg:p-12">
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

          {/* This footer is part of the right pane */}
          <AppFooter />
        </div>
      </div>
    </SidebarProvider>
  );
}
