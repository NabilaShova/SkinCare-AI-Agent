export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const DEFAULT_DASHBOARD_STORE_ID = Number(process.env.NEXT_PUBLIC_DEMO_STORE_ID ?? 1);

export function getDashboardStoreId(): number {
  if (typeof window === 'undefined') {
    return DEFAULT_DASHBOARD_STORE_ID;
  }
  const stored = window.localStorage.getItem('dashboard_store_id');
  if (!stored) {
    return DEFAULT_DASHBOARD_STORE_ID;
  }
  const parsed = Number(stored);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_DASHBOARD_STORE_ID;
}

export function setDashboardStoreId(storeId: number) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('dashboard_store_id', String(storeId));
}

export function getAdminApiKey(): string {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem('admin_api_key') ?? '';
}

export function setAdminApiKey(value: string) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('admin_api_key', value);
}

export async function fetcher(path: string, options?: RequestInit) {
  const normalizedPath = path.startsWith('/api') ? path : `/api${path}`;
  const adminKey = getAdminApiKey();
  const res = await fetch(`${apiUrl}${normalizedPath}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(adminKey ? { 'X-Admin-API-Key': adminKey } : {})
    },
    credentials: 'include',
    ...options
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export async function uploadKnowledge(storeId: number, file: File) {
  const adminKey = getAdminApiKey();
  const formData = new FormData();
  formData.append('store_id', String(storeId));
  formData.append('file', file);

  const res = await fetch(`${apiUrl}/api/knowledge/upload`, {
    method: 'POST',
    headers: adminKey ? { 'X-Admin-API-Key': adminKey } : undefined,
    body: formData
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}
