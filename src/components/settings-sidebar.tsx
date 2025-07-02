'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Sidebar,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarContent,
} from '@/components/ui/sidebar';
import { User, Palette, KeyRound, Info } from 'lucide-react';

const navItems = [
  { href: '/settings', label: 'Profile', icon: User },
  { href: '/settings/appearance', label: 'Appearance', icon: Palette },
  { href: '/settings/account', label: 'Account', icon: KeyRound },
  { href: '/settings/about', label: 'About', icon: Info },
];

export function SettingsSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar>
      <SidebarContent>
        <SidebarHeader>
          <h2 className="text-lg font-semibold">Settings</h2>
        </SidebarHeader>
        <SidebarMenu>
          {navItems.map((item) => (
            <SidebarMenuItem key={item.href}>
              <Link href={item.href} passHref legacyBehavior>
                <SidebarMenuButton
                  isActive={pathname === item.href}
                  tooltip={{ children: item.label }}
                >
                  <item.icon />
                  <span>{item.label}</span>
                </SidebarMenuButton>
              </Link>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
    </Sidebar>
  );
}
