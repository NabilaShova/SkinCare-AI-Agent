'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ChatBubble } from '@/components/chat-bubble';
import { fetcher } from '@/lib/api';

interface MessageItem {
  role: 'user' | 'assistant';
  content: string;
}

const starterPrompts = [
  'I have oily, acne-prone skin. What moisturizer should I use?',
  'Can I use Niacinamide with Vitamin C?',
  'Where is my order #3452?',
  'Do you ship internationally?'
];

export default function ChatPage() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [storeName, setStoreName] = useState('Glow Beauty Co.');
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function startConversation() {
      try {
        const data = await fetcher('/chat/start', {
          method: 'POST',
          body: JSON.stringify({ customer_name: 'Guest' })
        });
        setConversationId(data.conversation_id);
        setStoreName(data.store_name);
        setMessages([{ role: 'assistant', content: data.greeting }]);
      } catch (error) {
        console.error('Failed to start chat', error);
      } finally {
        setLoading(false);
      }
    }

    startConversation();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSend = async (text?: string) => {
    const content = (text ?? prompt).trim();
    if (!content || !conversationId || sending) return;

    setSending(true);
    setPrompt('');
    setMessages((current) => [...current, { role: 'user', content }]);

    try {
      const response = await fetcher('/chat/message', {
        method: 'POST',
        body: JSON.stringify({ conversation_id: conversationId, content })
      });
      if (response?.messages) {
        setMessages(response.messages);
      }
    } catch (error) {
      console.error('Failed to send message', error);
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: 'Sorry, I had trouble responding. Please try again in a moment.'
        }
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 py-6 sm:px-6">
        <header className="mb-6 flex items-center justify-between gap-4 rounded-3xl border border-slate-800 bg-slate-900/90 px-6 py-5 shadow-xl shadow-slate-950/40">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-pink-300">Skincare AI Consultant</p>
            <h1 className="mt-2 text-2xl font-semibold">{storeName}</h1>
            <p className="mt-1 text-sm text-slate-400">
              Product recommendations, ingredient guidance, policies, and order support
            </p>
          </div>
          <Link
            href="/dashboard"
            className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800"
          >
            Admin dashboard
          </Link>
        </header>

        <section className="flex min-h-0 flex-1 flex-col rounded-3xl border border-slate-800 bg-slate-900/90 shadow-xl shadow-slate-950/40">
          <div className="flex-1 space-y-2 overflow-y-auto p-6">
            {loading ? (
              <div className="rounded-3xl bg-slate-950/80 p-6 text-slate-400">Starting your skincare consultation…</div>
            ) : (
              messages.map((message, index) => (
                <ChatBubble key={`${message.role}-${index}`} role={message.role} message={message.content} />
              ))
            )}
            {sending ? (
              <div className="rounded-3xl bg-slate-950/80 px-5 py-4 text-sm text-slate-400">Thinking…</div>
            ) : null}
            <div ref={bottomRef} />
          </div>

          {!loading && messages.length <= 1 ? (
            <div className="border-t border-slate-800 px-6 py-4">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Try asking</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {starterPrompts.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => handleSend(item)}
                    className="rounded-full border border-slate-700 bg-slate-950/70 px-4 py-2 text-left text-sm text-slate-300 transition hover:border-pink-500/40 hover:text-white"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="border-t border-slate-800 px-6 py-5">
            <div className="flex gap-3">
              <input
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about products, ingredients, shipping, or your order..."
                className="min-w-0 flex-1 rounded-2xl border border-slate-800 bg-slate-950/90 px-4 py-3 text-slate-100 outline-none transition focus:border-pink-500"
              />
              <button
                type="button"
                onClick={() => handleSend()}
                disabled={sending || loading}
                className="rounded-2xl bg-pink-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-pink-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Send
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
