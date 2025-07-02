import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { SettingsSidebar } from '@/components/settings-sidebar';

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
