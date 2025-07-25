'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { User, Palette, KeyRound, Info } from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const navItems = [
  { href: '/settings', label: 'Profile', icon: User },
  { href: '/settings/appearance', label: 'Appearance', icon: Palette },
  { href: '/settings/account', label: 'Account', icon: KeyRound },
  { href: '/settings/about', label: 'About', icon: Info },
];

export function SettingsNav() {
  const pathname = usePathname();
  const router = useRouter();
  const isMobile = useIsMobile();
  
  if (isMobile === undefined) {
    return null; // or a loading skeleton
  }

  if (isMobile) {
    return (
      <div className="mb-6">
        <Select value={pathname} onValueChange={(value) => router.push(value)}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a setting" />
          </SelectTrigger>
          <SelectContent>
            {navItems.map((item) => (
              <SelectItem key={item.href} value={item.href}>
                <div className="flex items-center gap-2">
                  <item.icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  return (
    <nav className="flex flex-col gap-1">
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            'flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary',
            pathname === item.href && 'bg-muted font-medium text-primary'
          )}
        >
          <item.icon className="h-4 w-4" />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
