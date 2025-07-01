
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
import { motion, AnimatePresence } from 'framer-motion';

export function AppHeader() {
  const { isAuthenticated, login, logout } = useAuth();
  const { setTheme, theme } = useTheme();
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Generator' },
    { href: '/history', label: 'History' },
    { href: '/library', label: 'Library' },
  ];

  return (
    <header className="fixed top-0 z-30 flex h-16 w-full items-center gap-4 border-b bg-card px-4 sm:px-6">
      <div className="flex items-center gap-2">
        <Image src="/NavGAI-19.png" width={25} height={25} alt="NaviGator Logo" />
        <h1 className="text-xl font-bold tracking-tight">NaviGator Sailor</h1>
      </div>
      <nav className="ml-6 hidden items-center gap-1 text-sm font-medium md:flex">
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
                  animate={{ opacity: 1, transition: { duration: 0.25, ease: 'easeOut' } }}
                  exit={{ opacity: 0, transition: { duration: 0.1, ease: 'easeIn' } }}
                />
              )}
            </AnimatePresence>
            <span className="relative z-10">{item.label}</span>
          </Link>
        ))}
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
