import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Skincare AI Support',
  description: 'AI customer support agent for Shopify beauty stores'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
