import { AppHeader } from "@/components/app-header";
import { AppFooter } from "@/components/app-footer";
import { PromptHistoryClient } from "@/components/prompt-history-client";

export default function HistoryPage() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <div className="flex-1">
        <main>
          <PromptHistoryClient />
        </main>
      </div>
      <AppFooter />
    </div>
  );
}
