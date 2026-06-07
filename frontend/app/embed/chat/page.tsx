'use client';

import { useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { ChatPanel } from '@/components/chat-panel';

const DEFAULT_STORE_ID = Number(process.env.NEXT_PUBLIC_DEMO_STORE_ID ?? 1);

export default function EmbedChatPage() {
  const searchParams = useSearchParams();
  const storeId = useMemo(() => {
    const raw = searchParams.get('store_id');
    const parsed = raw ? Number(raw) : DEFAULT_STORE_ID;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_STORE_ID;
  }, [searchParams]);

  return (
    <div className="h-dvh">
      <ChatPanel storeId={storeId} embed showAdminLink={false} />
    </div>
  );
}
