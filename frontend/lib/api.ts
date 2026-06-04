export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetcher(path: string, options?: RequestInit) {
  const res = await fetch(`${apiUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'include',
    ...options
  });
  return res.json();
}
