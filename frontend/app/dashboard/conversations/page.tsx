'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChatBubble } from '@/components/chat-bubble';
import { SideNav } from '@/components/side-nav';
import { fetcher } from '@/lib/api';

interface ConversationSummary {
  id: number;
  title: string;
  customer: string;
  preview: string;
  last_activity: string;
  status: string;
  is_escalated: boolean;
}

interface MessageItem {
  role: 'user' | 'assistant';
  content: string;
}

const defaultConversation: ConversationSummary = {
  id: 0,
  title: 'Loading conversation…',
  customer: 'Customer',
  preview: '',
  last_activity: '',
  status: 'open',
  is_escalated: false
};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<number>(0);
  const [thread, setThread] = useState<MessageItem[]>([]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(true);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === selectedConversation) ?? defaultConversation,
    [conversations, selectedConversation]
  );

  useEffect(() => {
    async function loadConversations() {
      try {
        const data = await fetcher('/conversations?store_id=1');
        setConversations(data);
        if (data.length > 0) {
          setSelectedConversation(data[0].id);
        }
      } catch (error) {
        console.error('Failed to load conversations', error);
      }
    }
    loadConversations();
  }, []);

  useEffect(() => {
    async function loadConversationDetail() {
      if (!selectedConversation) return;
      setLoading(true);
      try {
        const data = await fetcher(`/conversations/${selectedConversation}`);
        setThread(data.messages);
      } catch (error) {
        console.error('Failed to load conversation detail', error);
      } finally {
        setLoading(false);
      }
    }
    loadConversationDetail();
  }, [selectedConversation]);

  const handleSend = async () => {
    if (!prompt.trim() || !selectedConversation) return;

    const userMessage: MessageItem = { role: 'user', content: prompt.trim() };
    setThread((current) => [...current, userMessage]);
    setPrompt('');

    try {
      const response = await fetcher('/conversations/message', {
        method: 'POST',
        body: JSON.stringify({ conversation_id: selectedConversation, role: 'user', content: userMessage.content })
      });
      if (response?.messages) {
        setThread(response.messages);
      }
    } catch (error) {
      console.error('Failed to send message', error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[280px_minmax(0,_1fr)]">
        <SideNav />

        <main className="flex flex-col gap-6 px-8 py-8">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl shadow-slate-950/40">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-pink-300">Conversations</p>
                <h1 className="mt-2 text-4xl font-semibold">Live support</h1>
              </div>
              <div className="rounded-3xl bg-slate-950/80 px-4 py-3 text-sm text-slate-300">
                AI chat routed to order, product, and FAQ agents
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,_1fr)]">
            <section className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl shadow-slate-950/40">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm uppercase tracking-[0.28em] text-pink-300">Conversations</p>
                  <h2 className="mt-2 text-xl font-semibold">Queued chats</h2>
                </div>
                <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-300">Live</span>
              </div>
              <div className="space-y-3">
                {conversations.length === 0 ? (
                  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4 text-slate-400">Loading conversations…</div>
                ) : (
                  conversations.map((conversation) => (
                    <button
                      key={conversation.id}
                      type="button"
                      onClick={() => setSelectedConversation(conversation.id)}
                      className={`w-full rounded-3xl border px-4 py-4 text-left transition ${
                        conversation.id === selectedConversation
                          ? 'border-pink-500/50 bg-pink-500/10 text-white'
                          : 'border-slate-800 bg-slate-950/50 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="font-semibold">{conversation.title}</p>
                          <p className="mt-1 text-sm text-slate-400">{conversation.preview}</p>
                        </div>
                        <span className="text-xs text-slate-500">{conversation.last_activity}</span>
                      </div>
                      <p className="mt-3 text-sm text-slate-400">Customer: {conversation.customer}</p>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="flex min-h-[680px] flex-col rounded-3xl border border-slate-800 bg-slate-900/90 shadow-xl shadow-slate-950/40">
              <div className="border-b border-slate-800 px-6 py-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.28em] text-pink-300">Conversation</p>
                    <h2 className="mt-2 text-2xl font-semibold">{activeConversation.title}</h2>
                    <p className="mt-1 text-sm text-slate-400">{activeConversation.customer} — Last activity {activeConversation.last_activity}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-950/70 px-3 py-1 text-xs uppercase tracking-[0.25em] text-slate-300">
                    Hybrid AI + escalation
                  </div>
                </div>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto p-6">
                {loading ? (
                  <div className="rounded-3xl bg-slate-950/80 p-6 text-slate-400">Loading chat history…</div>
                ) : thread.length === 0 ? (
                  <div className="rounded-3xl bg-slate-950/80 p-6 text-slate-400">No messages yet.</div>
                ) : (
                  thread.map((message, index) => (
                    <ChatBubble key={`${message.role}-${index}`} role={message.role} message={message.content} />
                  ))
                )}
              </div>

              <div className="border-t border-slate-800 px-6 py-5">
                <label className="block text-sm font-medium text-slate-400">Send a message</label>
                <div className="mt-3 flex gap-3">
                  <input
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    placeholder="Type a question about products, orders, or ingredients..."
                    className="min-w-0 flex-1 rounded-2xl border border-slate-800 bg-slate-950/90 px-4 py-3 text-slate-100 outline-none transition focus:border-pink-500"
                  />
                  <button
                    type="button"
                    onClick={handleSend}
                    className="rounded-2xl bg-pink-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-pink-400"
                  >
                    Send
                  </button>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
