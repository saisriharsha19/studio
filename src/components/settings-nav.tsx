'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { User, Palette, KeyRound, Info } from 'lucide-react';

const navItems = [
  { href: '/settings', label: 'Profile' },
  { href: '/settings/appearance', label: 'Appearance' },
  { href: '/settings/account', label: 'Account' },
  { href: '/settings/about', label: 'About' },
];

const navIcons: { [key: string]: React.ElementType } = {
  '/settings': User,
  '/settings/appearance': Palette,
  '/settings/account': KeyRound,
  '/settings/about': Info,
};

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <>
      {/* Desktop Navigation */}
      <nav className="hidden md:flex items-center space-x-2 lg:space-x-4 border-b">
        {navItems.map((item) => {
          const Icon = navIcons[item.href];
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2 whitespace-nowrap px-3 py-3 text-sm font-medium transition-colors hover:text-primary',
                pathname === item.href
                  ? 'border-b-2 border-primary text-primary'
                  : 'border-b-2 border-transparent text-muted-foreground'
              )}
            >
              {Icon && <Icon className="h-4 w-4" />}
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Mobile Navigation */}
      <div className="md:hidden">
        <ScrollArea className="w-full whitespace-nowrap">
          <nav className="flex w-max items-center space-x-1 border-b">
            {navItems.map((item) => {
              const Icon = navIcons[item.href];
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors',
                    pathname === item.href
                      ? 'border-b-2 border-primary text-primary'
                      : 'border-b-2 border-transparent text-muted-foreground hover:text-primary'
                  )}
                >
                  {Icon && <Icon className="h-4 w-4 flex-shrink-0" />}
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <ScrollBar orientation="horizontal" className="invisible" />
        </ScrollArea>
      </div>
    </>
  );
}
