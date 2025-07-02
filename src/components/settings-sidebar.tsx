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
  SidebarFooter,
  SidebarRail,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { User, Palette, KeyRound, Info, PanelLeftClose } from 'lucide-react';
import { Button } from './ui/button';

const navItems = [
  { href: '/settings', label: 'Profile', icon: User },
  { href: '/settings/appearance', label: 'Appearance', icon: Palette },
  { href: '/settings/account', label: 'Account', icon: KeyRound },
  { href: '/settings/about', label: 'About', icon: Info },
];

export function SettingsSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarRail />
      <SidebarContent>
        <SidebarHeader className="group-data-[state=expanded]:flex group-data-[state=collapsed]:hidden">
          <h2 className="text-lg font-semibold">Settings</h2>
        </SidebarHeader>
        <SidebarMenu>
          {navItems.map((item) => (
            <SidebarMenuItem key={item.href}>
              <SidebarMenuButton
                asChild
                isActive={pathname === item.href}
                tooltip={{ children: item.label }}
              >
                <Link href={item.href}>
                  <item.icon />
                  <span>{item.label}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter>
        <SidebarTrigger
          variant="ghost"
          className="w-full justify-start group-data-[state=collapsed]:hidden"
        >
          <PanelLeftClose />
          <span>Collapse</span>
        </SidebarTrigger>
      </SidebarFooter>
    </Sidebar>
  );
}
