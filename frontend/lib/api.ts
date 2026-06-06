export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetcher(path: string, options?: RequestInit) {
  const normalizedPath = path.startsWith('/api') ? path : `/api${path}`;
  const res = await fetch(`${apiUrl}${normalizedPath}`, {
    headers: {
      'Content-Type': 'application/json'
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
