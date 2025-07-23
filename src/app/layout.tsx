import type {Metadata} from 'next';
import './globals.css';
import { Toaster } from "@/components/ui/toaster"
import { AuthProvider } from '@/hooks/use-auth';
import { ThemeProvider } from '@/components/theme-provider';
import { PromptHistoryProvider } from '@/hooks/use-prompts';
import { PromptForgeProvider } from '@/hooks/use-prompt-forge';
import { LibraryProvider } from '@/hooks/use-library';

export const metadata: Metadata = {
  title: 'NaviGator Prompt',
  description: 'Create and iterate on prompts.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"></link>
      </head>
      <body className="font-body antialiased">
        <AuthProvider>
          <PromptHistoryProvider>
            <LibraryProvider>
              <PromptForgeProvider>
                <ThemeProvider
                  attribute="class"
                  defaultTheme="system"
                  enableSystem
                  disableTransitionOnChange
                >
                  {children}
                </ThemeProvider>
              </PromptForgeProvider>
            </LibraryProvider>
          </PromptHistoryProvider>
        </AuthProvider>
        <Toaster />
      </body>
    </html>
  );
}
