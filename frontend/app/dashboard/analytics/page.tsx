'use client';

import { useEffect, useState } from 'react';
import { SideNav } from '@/components/side-nav';
import { fetcher } from '@/lib/api';

interface MetricItem {
  label: string;
  value: string;
  change: string;
}

interface TrendItem {
  label: string;
  value: string;
}

interface PerformanceItem {
  label: string;
  percent: number;
}

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<MetricItem[]>([]);
  const [trendItems, setTrendItems] = useState<TrendItem[]>([]);
  const [performance, setPerformance] = useState<PerformanceItem[]>([]);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const data = await fetcher('/analytics');
        setMetrics(data.metrics ?? []);
        setTrendItems(data.trend_items ?? []);
        setPerformance(data.performance ?? []);
      } catch (error) {
        console.error('Failed to load analytics', error);
      }
    }
    loadAnalytics();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[280px_minmax(0,_1fr)]">
        <SideNav />

        <main className="px-8 py-10">
          <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
            <section className="rounded-3xl border border-slate-800 bg-slate-900/90 p-8 shadow-xl shadow-slate-950/40">
              <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-pink-300">Analytics</p>
                  <h1 className="mt-3 text-4xl font-semibold">Performance dashboard</h1>
                </div>
                <div className="rounded-3xl bg-slate-950/70 px-4 py-3 text-sm text-slate-300">
                  AI-driven metrics for growth and support quality
                </div>
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                {metrics.length === 0 ? (
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6 text-slate-400">Loading metrics…</div>
                ) : (
                  metrics.map((metric) => (
                    <div key={metric.label} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
                      <p className="text-sm uppercase tracking-[0.28em] text-slate-400">{metric.label}</p>
                      <div className="mt-3 flex items-end gap-3">
                        <p className="text-3xl font-semibold text-white">{metric.value}</p>
                        <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-300">
                          {metric.change}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-white">AI recommendation performance</h2>
                    <p className="mt-2 text-sm text-slate-400">Monitor product lift and assisted conversion signals.</p>
                  </div>
                  <span className="rounded-full bg-slate-900/90 px-3 py-1 text-xs uppercase tracking-[0.2em] text-slate-300">
                    Last 30 days
                  </span>
                </div>
                <div className="mt-6 space-y-4">
                  {performance.length === 0 ? (
                    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4 text-slate-400">Loading performance trends…</div>
                  ) : (
                    performance.map((item) => (
                      <div key={item.label}>
                        <div className="flex items-center justify-between text-sm text-slate-300">
                          <span>{item.label}</span>
                          <span>{item.percent}%</span>
                        </div>
                        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                          <div className="h-full rounded-full bg-pink-500" style={{ width: `${item.percent}%` }} />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>

            <section className="space-y-6">
              <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-7 shadow-xl shadow-slate-950/40">
                <h2 className="text-xl font-semibold">Top trend signals</h2>
                <div className="mt-5 space-y-4">
                  {trendItems.length === 0 ? (
                    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4 text-slate-400">Loading trends…</div>
                  ) : (
                    trendItems.map((item) => (
                      <div key={item.label} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
                        <p className="text-sm text-slate-400">{item.label}</p>
                        <p className="mt-2 font-semibold text-white">{item.value}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-7 shadow-xl shadow-slate-950/40">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.3em] text-pink-300">Engagement</p>
                    <h3 className="mt-2 text-2xl font-semibold">Message flow</h3>
                  </div>
                  <span className="rounded-full bg-slate-950/70 px-3 py-1 text-xs uppercase tracking-[0.2em] text-slate-300">
                    Live view
                  </span>
                </div>
                <div className="mt-8 grid gap-4">
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
                    <div className="mb-3 flex items-center justify-between text-sm text-slate-400">
                      <span>AI responses</span>
                      <span>1,230</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                      <div className="h-full rounded-full bg-pink-500" style={{ width: '70%' }} />
                    </div>
                  </div>
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
                    <div className="mb-3 flex items-center justify-between text-sm text-slate-400">
                      <span>Human escalations</span>
                      <span>84</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: '14%' }} />
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
