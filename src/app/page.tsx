import { AppHeader } from '@/components/app-header';
import { PromptForgeClient } from '@/components/prompt-forge-client';

export default function Home() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <main className="flex-1 p-4 sm:p-6 md:p-8">
        <PromptForgeClient />
      </main>
    </div>
  );
}
