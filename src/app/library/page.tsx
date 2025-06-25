import { AppHeader } from "@/components/app-header";
import { PromptLibraryClient } from "@/components/prompt-library-client";

export default function LibraryPage() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <main className="flex-1">
        <PromptLibraryClient />
      </main>
    </div>
  );
}
