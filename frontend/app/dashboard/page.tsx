import { MetricsCard } from '@/components/metrics-card';
import { SideNav } from '@/components/side-nav';

const metrics = [
  { label: 'Conversations', value: '1,248' },
  { label: 'Resolved', value: '1,023' },
  { label: 'Escalated', value: '78' },
  { label: 'CSAT', value: '95%' }
];

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[280px_minmax(0,_1fr)]">
        <SideNav />
        <main className="px-8 py-10">
          <div className="flex items-center justify-between gap-4 pb-8">
            <div>
              <p className="text-sm uppercase tracking-[0.28em] text-pink-300">Admin dashboard</p>
              <h1 className="mt-3 text-4xl font-semibold">Store performance</h1>
            </div>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map((item) => (
              <MetricsCard key={item.label} label={item.label} value={item.value} />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
