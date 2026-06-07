import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-10 shadow-2xl shadow-slate-950/40">
          <div className="space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-pink-300">Beauty AI Support</p>
            <h1 className="text-5xl font-semibold tracking-tight text-white">AI Support for Shopify Beauty Stores</h1>
            <p className="max-w-2xl text-lg text-slate-300">
              Connect your Shopify store, sync skincare and hair care products, ingest knowledge documents, and deliver intelligent customer support on your storefront chat widget.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                href="/chat?store_id=3"
                className="rounded-full bg-pink-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-pink-400"
              >
                Chat with AI advisor
              </Link>
              <Link href="/dashboard" className="rounded-full border border-slate-700 px-6 py-3 text-sm text-slate-200 transition hover:bg-slate-800/80">
                Open admin dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
