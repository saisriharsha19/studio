import { AppHeader } from "@/components/app-header";
import { PromptHistoryClient } from "@/components/prompt-history-client";

export default function HistoryPage() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <main className="flex-1">
        <PromptHistoryClient />
      </main>
    </div>
  );
}
