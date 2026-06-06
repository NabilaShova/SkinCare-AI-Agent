'use client';

import { useEffect, useState } from 'react';
import { SideNav } from '@/components/side-nav';
import { fetcher } from '@/lib/api';

interface ProductItem {
  id: number;
  title: string;
  description?: string;
  ingredients?: string;
  price?: string;
  available: boolean;
  collections?: string[];
}

export default function ProductsPage() {
  const [storeId, setStoreId] = useState(1);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [status, setStatus] = useState('Loading products...');

  useEffect(() => {
    async function loadProducts() {
      try {
        const data = await fetcher(`/shopify/products?store_id=${storeId}`);
        setProducts(data.items ?? []);
        setStatus(`${data.items?.length ?? 0} products loaded from store #${storeId}.`);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : 'Failed to load products.');
      }
    }
    loadProducts();
  }, [storeId]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[280px_minmax(0,_1fr)]">
        <SideNav />
        <main className="px-8 py-10">
          <p className="text-sm uppercase tracking-[0.28em] text-pink-300">Products</p>
          <h1 className="mt-3 text-4xl font-semibold">Synced catalog</h1>

          <div className="mt-6 flex items-center gap-3">
            <label className="text-sm text-slate-400">Store ID</label>
            <input
              type="number"
              value={storeId}
              onChange={(event) => setStoreId(Number(event.target.value))}
              className="w-28 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-2"
            />
            <span className="text-sm text-slate-500">{status}</span>
          </div>

          <div className="mt-8 grid gap-4 xl:grid-cols-2">
            {products.map((product) => (
              <article key={product.id} className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5">
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-lg font-semibold">{product.title}</h2>
                  <span className="text-sm text-pink-300">{product.price}</span>
                </div>
                <p className="mt-3 text-sm text-slate-400">{product.description}</p>
                {product.ingredients ? (
                  <p className="mt-3 text-xs text-slate-500">Ingredients: {product.ingredients}</p>
                ) : null}
                <p className="mt-3 text-xs uppercase tracking-[0.2em] text-slate-500">
                  {product.available ? 'Available' : 'Unavailable'}
                </p>
              </article>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
