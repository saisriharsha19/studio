import { AppHeader } from '@/components/app-header';
import { PromptForgeClient } from '@/components/prompt-forge-client';
import { AppFooter } from '@/components/app-footer';

export default function Home() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <div className="flex-1">
        <main className="p-6 sm:p-8 md:p-10">
          <h1 className="sr-only">Navigator Sailor</h1>
          <PromptForgeClient />
        </main>
      </div>
      <AppFooter />
    </div>
  );
}
