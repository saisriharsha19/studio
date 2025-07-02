'use client';

import { useAuth } from '@/hooks/use-auth';
import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { SettingsSidebar } from '@/components/settings-sidebar';
import { Button } from '@/components/ui/button';
import { UserCircle } from 'lucide-react';

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, login } = useAuth();

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full flex-col bg-background">
        <AppHeader />
        <div className="mt-16 flex flex-1">
          <SettingsSidebar />
          <SidebarInset>
            {/* Mobile-only header with trigger */}
            <header className="sticky top-16 z-10 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
              <SidebarTrigger />
              <h1 className="text-lg font-semibold">Settings</h1>
            </header>
            <main className="flex-1 p-6 sm:p-8 md:p-10">
              {isAuthenticated ? (
                children
              ) : (
                <div className="flex h-full flex-col items-center justify-center rounded-lg border-2 border-dashed bg-muted/50 p-12 text-center">
                  <UserCircle className="h-16 w-16 text-muted-foreground" />
                  <h2 className="mt-6 text-2xl font-semibold tracking-tight">Access Your Settings</h2>
                  <p className="mt-2 text-muted-foreground">
                    Sign in with your GatorLink to manage your profile, appearance, and account settings.
                  </p>
                  <Button onClick={login} className="mt-6">
                    Sign In with GatorLink
                  </Button>
                </div>
              )}
            </main>
          </SidebarInset>
        </div>
        <AppFooter />
      </div>
    </SidebarProvider>
  );
}
