'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { fetcher, getDashboardStoreId } from '@/lib/api';

const nav = [
  { label: 'Customer Chat', href: '/chat' },
  { label: 'Overview', href: '/dashboard' },
  { label: 'Conversations', href: '/dashboard/conversations' },
  { label: 'Knowledge Base', href: '/dashboard/knowledge' },
  { label: 'Products', href: '/dashboard/products' },
  { label: 'Analytics', href: '/dashboard/analytics' },
  { label: 'Settings', href: '/dashboard/settings' }
];

const DEFAULT_STORE_NAME = process.env.NEXT_PUBLIC_STORE_NAME ?? 'Glow Beauty Co.';

function isActiveRoute(pathname: string, href: string): boolean {
  if (href === '/dashboard') {
    return pathname === '/dashboard';
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SideNav() {
  const pathname = usePathname();
  const [storeName, setStoreName] = useState(DEFAULT_STORE_NAME);

  useEffect(() => {
    async function loadStoreName() {
      try {
        const storeId = getDashboardStoreId();
        const data = await fetcher(`/shopify/store-info?store_id=${storeId}`);
        if (data?.name) {
          setStoreName(data.name);
        }
      } catch {
        setStoreName(DEFAULT_STORE_NAME);
      }
    }

    loadStoreName();
  }, []);

  return (
    <aside className="border-r border-slate-800 bg-slate-950 px-6 py-8">
      <div className="space-y-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-pink-300">Skincare AI</p>
          <h2 className="mt-4 text-2xl font-semibold">{storeName}</h2>
        </div>
        <nav className="space-y-2">
          {nav.map((item) => {
            const active = isActiveRoute(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={`block rounded-2xl px-4 py-3 text-sm transition ${
                  active
                    ? 'bg-pink-500/10 font-medium text-pink-200'
                    : 'text-slate-200 hover:bg-slate-900/80'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
