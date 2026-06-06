'use client';

import { useEffect, useState } from 'react';
import { SideNav } from '@/components/side-nav';
import { fetcher, getDashboardStoreId, setDashboardStoreId, uploadKnowledge } from '@/lib/api';

interface DocumentItem {
  id: number;
  filename: string;
  content_type: string;
  status: string;
  created_at: string;
}

export default function KnowledgePage() {
  const [storeId, setStoreId] = useState(() => getDashboardStoreId());

  useEffect(() => {
    setDashboardStoreId(storeId);
  }, [storeId]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [status, setStatus] = useState('');
  const [uploading, setUploading] = useState(false);

  async function loadDocuments() {
    try {
      const data = await fetcher(`/knowledge?store_id=${storeId}`);
      setDocuments(data.items ?? []);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Failed to load documents.');
    }
  }

  useEffect(() => {
    loadDocuments();
  }, [storeId]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus(`Uploading ${file.name}...`);
    try {
      const result = await uploadKnowledge(storeId, file);
      setStatus(`Indexed ${result.chunks_indexed} chunks from ${result.filename}.`);
      await loadDocuments();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Upload failed.');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const handleDelete = async (documentId: number) => {
    try {
      await fetcher(`/knowledge/${documentId}?store_id=${storeId}`, { method: 'DELETE' });
      setStatus('Document deleted.');
      await loadDocuments();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Delete failed.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[280px_minmax(0,_1fr)]">
        <SideNav />
        <main className="px-8 py-10">
          <p className="text-sm uppercase tracking-[0.28em] text-pink-300">Knowledge Base</p>
          <h1 className="mt-3 text-4xl font-semibold">Documents & FAQ</h1>

          <section className="mt-8 max-w-4xl rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
            <div className="flex flex-wrap items-center gap-4">
              <label className="text-sm text-slate-400">Store ID</label>
              <input
                type="number"
                value={storeId}
                onChange={(event) => setStoreId(Number(event.target.value))}
                className="w-28 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-2"
              />
              <label className="cursor-pointer rounded-2xl bg-pink-500 px-5 py-3 text-sm font-semibold">
                {uploading ? 'Uploading...' : 'Upload document'}
                <input type="file" accept=".txt,.md,.pdf" className="hidden" onChange={handleUpload} disabled={uploading} />
              </label>
            </div>
            <p className="mt-3 text-sm text-slate-400">Supported: .txt, .md, .pdf (policies, ingredient guides, FAQs)</p>
          </section>

          <section className="mt-6 max-w-4xl space-y-3">
            {documents.length === 0 ? (
              <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 text-slate-400">No documents uploaded yet.</div>
            ) : (
              documents.map((document) => (
                <div key={document.id} className="flex items-center justify-between rounded-3xl border border-slate-800 bg-slate-900/90 p-5">
                  <div>
                    <p className="font-semibold">{document.filename}</p>
                    <p className="text-sm text-slate-400">
                      {document.status} · {new Date(document.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(document.id)}
                    className="rounded-2xl border border-slate-700 px-4 py-2 text-sm"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </section>

          {status ? <p className="mt-6 text-sm text-emerald-300">{status}</p> : null}
        </main>
      </div>
    </div>
  );
}
