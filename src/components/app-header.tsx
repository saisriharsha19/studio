'use client';

import Link from 'next/link';
import { Menu, Moon, Sun, UserCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Image from 'next/image';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { useAuth } from '@/hooks/use-auth';
import { useTheme } from 'next-themes';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { SidebarTrigger } from '@/components/ui/sidebar';

export function AppHeader({ isPaneHeader = false }: { isPaneHeader?: boolean }) {
  const { isAuthenticated, login, logout } = useAuth();
  const { setTheme, theme } = useTheme();
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Generator' },
    { href: '/history', label: 'History' },
    { href: '/library', label: 'Library' },
  ];

  return (
    <header className={cn(
      "flex h-16 shrink-0 items-center gap-4 border-b px-4 sm:px-6",
      isPaneHeader ? "bg-transparent" : "fixed top-0 z-30 w-full bg-card"
    )}>
      {!isPaneHeader ? (
        <>
          <nav className="hidden flex-col gap-6 text-lg font-medium md:flex md:flex-row md:items-center md:gap-5 md:text-sm lg:gap-6">
            <Link
              href="/"
              className="flex items-center gap-2 text-lg font-semibold md:text-base"
            >
              <Image
                src="/NavGAI-19.png"
                width={25}
                height={25}
                alt="NaviGator Logo"
              />
              <h1 className="text-xl font-bold tracking-tight">NaviGator Sailor</h1>
            </Link>
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'relative rounded-full px-3 py-1.5 transition-colors duration-300',
                  pathname === item.href
                    ? 'text-accent-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <AnimatePresence>
                  {pathname === item.href && (
                    <motion.span
                      className="absolute inset-0 z-0 rounded-full bg-accent"
                      initial={{ opacity: 0 }}
                      animate={{
                        opacity: 1,
                        transition: { duration: 0.25, ease: 'easeOut' },
                      }}
                      exit={{
                        opacity: 0,
                        transition: { duration: 0.1, ease: 'easeIn' },
                      }}
                    />
                  )}
                </AnimatePresence>
                <span className="relative z-10">{item.label}</span>
              </Link>
            ))}
          </nav>

          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="shrink-0 md:hidden"
              >
                <Menu className="h-5 w-5" />
                <span className="sr-only">Toggle navigation menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left">
              <SheetHeader className="sr-only">
                <SheetTitle>Navigation Menu</SheetTitle>
                <SheetDescription>Select a page to navigate to.</SheetDescription>
              </SheetHeader>
              <nav className="grid gap-6 text-lg font-medium">
                <Link
                  href="/"
                  className="flex items-center gap-2 text-lg font-semibold"
                >
                  <Image
                    src="/NavGAI-19.png"
                    width={25}
                    height={25}
                    alt="NaviGator Logo"
                  />
                  <span className="font-bold">NaviGator Sailor</span>
                </Link>
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'text-muted-foreground hover:text-foreground',
                      pathname === item.href && 'font-semibold text-foreground'
                    )}
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
        </>
      ) : (
        <SidebarTrigger className="md:hidden"/>
      )}

      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme('light')}>
              Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('dark')}>
              Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('system')}>
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <UserCircle className="h-6 w-6" />
              <span className="sr-only">Toggle user menu</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {isAuthenticated ? (
              <>
                <DropdownMenuItem asChild>
                  <Link href="/settings" className="cursor-pointer">
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={logout}
                  className="cursor-pointer"
                >
                  Sign Out
                </DropdownMenuItem>
              </>
            ) : (
              <DropdownMenuItem onClick={login} className="cursor-pointer">
                Sign In with GatorLink
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
