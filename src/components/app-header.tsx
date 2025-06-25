'use client';

import Link from 'next/link';
import { Moon, Sun, UserCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Image from 'next/image'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/hooks/use-auth';
import { useTheme } from 'next-themes';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

export function AppHeader() {
  const { isAuthenticated, login, logout } = useAuth();
  const { setTheme, theme } = useTheme();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-card px-4 sm:px-6">
      <div className="flex items-center gap-2">
        <Image src="/NavGAI-19.png" width={25} height={25} alt="NaviGator Logo" />
        <h1 className="text-xl font-bold tracking-tight">NaviGator Sailor</h1>
      </div>
      <nav className="ml-6 hidden items-center gap-6 text-sm font-medium md:flex">
        <Link
          href="/"
          className={cn(
            "transition-colors hover:text-foreground",
            pathname === '/' ? 'text-primary font-bold' : 'text-muted-foreground'
          )}
        >
          Generator
        </Link>
        <Link
          href="/library"
          className={cn(
            "transition-colors hover:text-foreground",
            pathname === '/library' ? 'text-primary font-bold' : 'text-muted-foreground'
          )}
        >
          Library
        </Link>
      </nav>
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
            <DropdownMenuItem onClick={() => setTheme("light")}>
              Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("dark")}>
              Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("system")}>
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full hover:bg-muted">
              <UserCircle className="h-6 w-6" />
              <span className="sr-only">Toggle user menu</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {isAuthenticated ? (
              <>
                <DropdownMenuItem className="cursor-pointer">University Profile</DropdownMenuItem>
                <DropdownMenuItem className="cursor-pointer">Settings</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="cursor-pointer">Sign Out</DropdownMenuItem>
              </>
            ) : (
              <DropdownMenuItem onClick={login} className="cursor-pointer">Sign In</DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
