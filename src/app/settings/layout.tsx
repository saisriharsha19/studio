'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { SettingsSidebar } from '@/components/settings-sidebar';
import { Skeleton } from '@/components/ui/skeleton';

function SettingsSkeleton() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <main className="mt-16 flex-1 p-6 sm:p-8 md:p-10">
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="mt-8 space-y-8">
          <Skeleton className="h-48 w-full rounded-lg" />
          <Skeleton className="h-32 w-full rounded-lg" />
        </div>
      </main>
      <AppFooter />
    </div>
  );
}

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Since the dummy auth provider initializes with isAuthenticated=false and has no loading state,
    // this effect will run on the initial render and redirect if the user is not logged in.
    if (!isAuthenticated) {
      router.replace('/');
    }
  }, [isAuthenticated, router]);

  // To prevent the settings UI from flashing before the redirect,
  // we render a skeleton loading state if the user is not authenticated.
  if (!isAuthenticated) {
    return <SettingsSkeleton />;
  }

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
            <main className="flex-1 p-6 sm:p-8 md:p-10">{children}</main>
          </SidebarInset>
        </div>
        <AppFooter />
      </div>
    </SidebarProvider>
  );
}
