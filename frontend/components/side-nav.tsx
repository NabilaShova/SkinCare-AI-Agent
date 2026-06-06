import Link from 'next/link';

const nav = [
  { label: 'Customer Chat', href: '/chat' },
  { label: 'Overview', href: '/dashboard' },
  { label: 'Conversations', href: '/dashboard/conversations' },
  { label: 'Knowledge Base', href: '/dashboard/knowledge' },
  { label: 'Products', href: '/dashboard/products' },
  { label: 'Analytics', href: '/dashboard/analytics' },
  { label: 'Settings', href: '/dashboard/settings' }
];

export function SideNav() {
  return (
    <aside className="border-r border-slate-800 bg-slate-950 px-6 py-8">
      <div className="space-y-10">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-pink-300">Skincare AI</p>
          <h2 className="mt-4 text-2xl font-semibold">Beauty Support</h2>
        </div>
        <nav className="space-y-2">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-2xl px-4 py-3 text-sm text-slate-200 transition hover:bg-slate-900/80"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
