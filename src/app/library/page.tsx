import { AppHeader } from "@/components/app-header";
import { AppFooter } from "@/components/app-footer";
import { LibraryClient } from "@/components/library-client";

export default function LibraryPage() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <main className="mt-16 flex-1">
        <LibraryClient />
      </main>
      <AppFooter />
    </div>
  );
}
