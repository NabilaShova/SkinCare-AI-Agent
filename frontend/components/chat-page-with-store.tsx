'use client';

import { Suspense, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { ChatPanel } from '@/components/chat-panel';

const DEFAULT_STORE_ID = Number(process.env.NEXT_PUBLIC_DEMO_STORE_ID ?? 1);

interface ChatPageWithStoreProps {
  embed?: boolean;
  showAdminLink?: boolean;
}

function resolveStoreId(raw: string | null): number {
  const parsed = raw ? Number(raw) : DEFAULT_STORE_ID;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_STORE_ID;
}

function ChatStoreResolver({ embed = false, showAdminLink = true }: ChatPageWithStoreProps) {
  const searchParams = useSearchParams();
  const storeId = useMemo(() => resolveStoreId(searchParams.get('store_id')), [searchParams]);

  if (embed) {
    return (
      <div className="h-dvh">
        <ChatPanel storeId={storeId} embed showAdminLink={false} />
      </div>
    );
  }

  return <ChatPanel storeId={storeId} showAdminLink={showAdminLink} />;
}

function ChatLoadingShell({ embed = false }: { embed?: boolean }) {
  return (
    <div className={embed ? 'h-dvh bg-slate-950' : 'min-h-screen bg-slate-950'}>
      <div className="flex h-full min-h-[240px] items-center justify-center text-sm text-slate-400">
        Loading chat…
      </div>
    </div>
  );
}

export function ChatPageWithStore({ embed = false, showAdminLink = true }: ChatPageWithStoreProps) {
  return (
    <Suspense fallback={<ChatLoadingShell embed={embed} />}>
      <ChatStoreResolver embed={embed} showAdminLink={showAdminLink} />
    </Suspense>
  );
}
