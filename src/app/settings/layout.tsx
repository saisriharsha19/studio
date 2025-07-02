import { AppHeader } from '@/components/app-header';
import { AppFooter } from '@/components/app-footer';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
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
        <main className="mt-16 flex flex-1">
          <SettingsSidebar />
          <SidebarInset>
            <div className="p-6 sm:p-8 md:p-10">{children}</div>
          </SidebarInset>
        </main>
        <AppFooter />
      </div>
    </SidebarProvider>
  );
}
