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
      {/* 
        This is the main page container. `h-screen` ensures it doesn't grow beyond the viewport.
        `flex-col` arranges header, content, and footer vertically.
      */}
      <div className="flex h-screen w-full flex-col bg-background">
        {/* AppHeader is fixed, so it's not part of the flex flow, but we account for its height below. */}
        <AppHeader />
        
        {/* 
          This container holds the main content (sidebar + pane).
          - flex-1: It grows to fill the vertical space between the header and footer.
          - mt-16: Accounts for the fixed header's height.
          - min-h-0: CRITICAL FIX. Allows this flex item to shrink below its content's intrinsic size, preventing it from pushing the footer down.
        */}
        <div className="flex flex-1 min-h-0 mt-16">
          <SettingsSidebar />

          {/* 
            This is the main content pane. `flex-1` makes it fill the horizontal space next to the sidebar.
            `overflow-y-auto` makes THIS pane, and only this pane, scrollable if its content is too tall.
          */}
          <main className="flex-1 overflow-y-auto">
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
        </div>
        
        {/* The AppFooter sits securely at the bottom of the flex column. */}
        <AppFooter />
      </div>
    </SidebarProvider>
  );
}
