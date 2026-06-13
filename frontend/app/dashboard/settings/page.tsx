'use client';

import { useEffect, useState } from 'react';
import { SideNav } from '@/components/side-nav';
import { apiUrl, fetcher, getAdminApiKey, getDashboardStoreId, setAdminApiKey, setDashboardStoreId } from '@/lib/api';

interface StoreItem {
  id: number;
  name: string;
  shopify_domain: string;
  scopes?: string;
  last_synced_at?: string | null;
}

export default function SettingsPage() {
  const [shopDomain, setShopDomain] = useState('');
  const [adminKey, setAdminKey] = useState('');
  const [storeId, setStoreId] = useState(() => getDashboardStoreId());
  const [stores, setStores] = useState<StoreItem[]>([]);
  const [status, setStatus] = useState('');
  const [loadError, setLoadError] = useState('');
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    setDashboardStoreId(storeId);
  }, [storeId]);

  useEffect(() => {
    setAdminKey(getAdminApiKey());
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('connected') === '1') {
        const connectedStoreId = Number(params.get('store_id') || 1);
        setStoreId(connectedStoreId);
        setStatus(`Shopify store connected successfully (store #${connectedStoreId}).`);
      }
    }
  }, []);

  useEffect(() => {
    async function loadStores() {
      setLoadError('');
      try {
        const data = await fetcher('/auth/status');
        setStores(data.stores ?? []);
      } catch (error) {
        setStores([]);
        const message = error instanceof Error ? error.message : 'Could not load connected stores.';
        if (message.includes('Invalid admin API key') || message.includes('401')) {
          setLoadError(
            'Invalid admin API key. Paste the exact ADMIN_API_KEY from Render (skincare-api → Environment), click Save, then reload this page.'
          );
        } else {
          setLoadError(message);
        }
      }
    }
    if (getAdminApiKey()) {
      loadStores();
    }
  }, [status]);

  const saveAdminKey = () => {
    setAdminApiKey(adminKey.trim());
    setStatus('Admin API key saved locally.');
    setLoadError('');
  };

  const connectShopify = () => {
    if (!shopDomain.trim()) {
      setStatus('Enter your Shopify shop domain first.');
      return;
    }
    const normalized = shopDomain.includes('.myshopify.com')
      ? shopDomain.trim()
      : `${shopDomain.trim()}.myshopify.com`;
    window.location.href = `${apiUrl}/api/auth/start?shop=${encodeURIComponent(normalized)}`;
  };

  const syncStore = async () => {
    setSyncing(true);
    setStatus('Syncing Shopify catalog, orders, and customers...');
    try {
      const result = await fetcher(`/shopify/sync?store_id=${storeId}`, { method: 'POST' });
      const warningText =
        Array.isArray(result.warnings) && result.warnings.length > 0
          ? ` Warnings: ${result.warnings.join(' ')}`
          : '';
      setStatus(
        `Sync ${result.status}: ${result.products_synced} products, ${result.orders_synced} orders, ${result.customers_synced} customers.${warningText}`
      );
      const data = await fetcher('/auth/status');
      setStores(data.stores ?? []);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[280px_minmax(0,_1fr)]">
        <SideNav />
        <main className="px-8 py-10">
          <p className="text-sm uppercase tracking-[0.28em] text-pink-300">Settings</p>
          <h1 className="mt-3 text-4xl font-semibold">Production setup</h1>

          <section className="mt-8 max-w-3xl rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
            <h2 className="text-xl font-semibold">Admin API key</h2>
            <p className="mt-2 text-sm text-slate-400">Required for sync, knowledge upload, and store management in production.</p>
            <div className="mt-4 flex gap-3">
              <input
                value={adminKey}
                onChange={(event) => setAdminKey(event.target.value)}
                placeholder="Enter ADMIN_API_KEY"
                className="min-w-0 flex-1 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3"
              />
              <button type="button" onClick={saveAdminKey} className="rounded-2xl bg-pink-500 px-5 py-3 text-sm font-semibold">
                Save
              </button>
            </div>
          </section>

          <section className="mt-6 max-w-3xl rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
            <h2 className="text-xl font-semibold">Connect Shopify store</h2>
            <p className="mt-2 text-sm text-slate-400">Start OAuth and sync live products, orders, and customers.</p>
            <div className="mt-4 flex gap-3">
              <input
                value={shopDomain}
                onChange={(event) => setShopDomain(event.target.value)}
                placeholder="your-store.myshopify.com"
                className="min-w-0 flex-1 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3"
              />
              <button type="button" onClick={connectShopify} className="rounded-2xl bg-pink-500 px-5 py-3 text-sm font-semibold">
                Connect
              </button>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <label className="text-sm text-slate-400">Active store ID</label>
              <input
                type="number"
                value={storeId}
                onChange={(event) => setStoreId(Number(event.target.value))}
                className="w-28 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-2"
              />
              <button
                type="button"
                onClick={syncStore}
                disabled={syncing}
                className="rounded-2xl border border-slate-700 px-5 py-2 text-sm disabled:opacity-60"
              >
                {syncing ? 'Syncing...' : 'Sync now'}
              </button>
            </div>
          </section>

          <section className="mt-6 max-w-3xl rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
            <h2 className="text-xl font-semibold">Connected stores</h2>
            <div className="mt-4 space-y-3">
              {loadError ? (
                <p className="rounded-2xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                  {loadError}
                </p>
              ) : null}
              {stores.length === 0 ? (
                <p className="text-slate-400">
                  No connected stores loaded. Save your admin API key above — your Shopify OAuth connection is stored on
                  the server and may still exist even if this list is empty.
                </p>
              ) : (
                stores.map((store) => (
                  <div key={store.id} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                    <p className="font-semibold">{store.name}</p>
                    <p className="text-sm text-slate-400">{store.shopify_domain}</p>
                    <p className="mt-2 text-xs text-slate-500">
                      Last synced: {store.last_synced_at ? new Date(store.last_synced_at).toLocaleString() : 'Never'}
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>

          {status ? <p className="mt-6 text-sm text-emerald-300">{status}</p> : null}
        </main>
      </div>
    </div>
  );
}
