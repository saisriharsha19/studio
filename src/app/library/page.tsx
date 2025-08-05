import { AppHeader } from "@/components/app-header";
import { AppFooter } from "@/components/app-footer";
import { LibraryClient } from "@/components/library-client";

export default function LibraryPage() {
  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      <AppHeader />
      <div className="flex-1">
        <main>
          <LibraryClient />
        </main>
      </div>
      <AppFooter />
    </div>
  );
}
