'use client';

import { useAuth } from '@/hooks/use-auth';
import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import { Button } from '@/components/ui/button';
import { UserCircle } from 'lucide-react';
import { SettingsNav } from '@/components/settings-nav';
import * as React from 'react';

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, login } = useAuth();

  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/40">
      <AppHeader />
      <main className="flex-1">
        <div className="container mx-auto max-w-5xl py-8 px-4 sm:px-6 lg:px-8">
            <div className="mb-8">
                <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground">
                    Manage your account settings and preferences.
                </p>
            </div>
            <div className="grid grid-cols-1 gap-12">
                {isAuthenticated ? (
                   <div className='rounded-lg border bg-card'>
                     <SettingsNav />
                     <div className="p-6 pt-8">
                        {children}
                     </div>
                   </div>
                ) : (
                <div className="flex flex-col h-full min-h-[40vh] items-center justify-center rounded-lg border-2 border-dashed bg-card p-6 text-center sm:p-8 lg:p-12">
                    <UserCircle className="h-12 w-12 text-muted-foreground sm:h-16 sm:w-16" />
                    <h2 className="mt-6 text-xl font-semibold tracking-tight sm:text-2xl">Access Your Settings</h2>
                    <p className="mt-2 text-muted-foreground">
                    Sign in with your GatorLink to manage your profile, appearance, and account settings.
                    </p>
                    <Button onClick={login} className="mt-6">
                    Sign In with GatorLink
                    </Button>
                </div>
                )}
            </div>
        </div>
      </main>
      <AppFooter />
    </div>
  );
}
