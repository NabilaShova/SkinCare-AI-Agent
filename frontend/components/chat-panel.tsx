'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ChatBubble } from '@/components/chat-bubble';
import { fetcher } from '@/lib/api';

interface MessageItem {
  role: 'user' | 'assistant';
  content: string;
  id?: number;
}

interface ChatPanelProps {
  storeId: number;
  embed?: boolean;
  showAdminLink?: boolean;
}

const starterPrompts = [
  'I have oily, acne-prone skin. What moisturizer should I use?',
  'Can I use Niacinamide with Vitamin C?',
  'What shampoo helps with hair fall?',
  'Do you ship internationally?'
];

export function ChatPanel({ storeId, embed = false, showAdminLink = true }: ChatPanelProps) {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [storeName, setStoreName] = useState('Beauty Store');
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [feedbackByMessageId, setFeedbackByMessageId] = useState<
    Record<number, 'idle' | 'sending' | 'helpful' | 'not_helpful'>
  >({});
  const bottomRef = useRef<HTMLDivElement>(null);

  const startConversation = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetcher('/chat/start', {
        method: 'POST',
        body: JSON.stringify({ customer_name: 'Guest', store_id: storeId })
      });
      setConversationId(data.conversation_id);
      setStoreName(data.store_name);
      setMessages([{ role: 'assistant', content: data.greeting }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start chat';
      setError(`Could not connect to the AI service. ${message}`);
      setMessages([]);
      setConversationId(null);
    } finally {
      setLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    startConversation();
  }, [startConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSend = async (text?: string) => {
    const content = (text ?? prompt).trim();
    if (!content || !conversationId || sending) return;

    setSending(true);
    setError('');
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
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Request failed';
      setError(`Failed to send message: ${message}`);
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

  const handleStarterClick = (item: string) => {
    setPrompt(item);
    setError('');
  };

  const handleFeedback = async (messageId: number, helpful: boolean) => {
    setFeedbackByMessageId((current) => ({ ...current, [messageId]: 'sending' }));
    try {
      await fetcher('/chat/feedback', {
        method: 'POST',
        body: JSON.stringify({ message_id: messageId, helpful })
      });
      setFeedbackByMessageId((current) => ({
        ...current,
        [messageId]: helpful ? 'helpful' : 'not_helpful'
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Feedback failed';
      setError(`Could not save feedback: ${message}`);
      setFeedbackByMessageId((current) => ({ ...current, [messageId]: 'idle' }));
    }
  };

  const ready = !loading && conversationId !== null;
  const shellClass = embed
    ? 'flex h-full min-h-0 flex-col bg-slate-950 text-slate-100'
    : 'min-h-screen bg-slate-950 text-slate-100';

  return (
    <div className={shellClass}>
      <div className={`mx-auto flex min-h-0 flex-1 flex-col ${embed ? 'h-full px-3 py-3' : 'min-h-screen max-w-5xl px-4 py-6 sm:px-6'}`}>
        <header
          className={`mb-4 flex items-center justify-between gap-4 rounded-3xl border border-slate-800 bg-slate-900/90 px-5 py-4 shadow-xl shadow-slate-950/40 ${embed ? 'mb-3 rounded-2xl py-3' : ''}`}
        >
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-pink-300">AI Beauty Advisor</p>
            <h1 className={`mt-1 font-semibold ${embed ? 'text-lg' : 'mt-2 text-2xl'}`}>{storeName}</h1>
            {!embed ? (
              <p className="mt-1 text-sm text-slate-400">
                Product recommendations, ingredient guidance, policies, and order support
              </p>
            ) : null}
          </div>
          {showAdminLink && !embed ? (
            <a
              href="/dashboard"
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800"
            >
              Admin dashboard
            </a>
          ) : null}
        </header>

        {error ? (
          <div className="mb-3 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
            {!ready ? (
              <button
                type="button"
                onClick={startConversation}
                className="ml-3 rounded-full border border-red-400/50 px-3 py-1 text-xs font-semibold"
              >
                Retry
              </button>
            ) : null}
          </div>
        ) : null}

        <section className="flex min-h-0 flex-1 flex-col rounded-3xl border border-slate-800 bg-slate-900/90 shadow-xl shadow-slate-950/40">
          <div className="flex-1 space-y-2 overflow-y-auto p-4 sm:p-6">
            {loading ? (
              <div className="rounded-3xl bg-slate-950/80 p-6 text-slate-400">
                Starting your consultation… (first load may take up to 60 seconds)
              </div>
            ) : (
              messages.map((message, index) => (
                <ChatBubble
                  key={message.id ?? `${message.role}-${index}`}
                  role={message.role}
                  message={message.content}
                  messageId={message.id}
                  showFeedback={message.role === 'assistant' && index > 0 && Boolean(message.id)}
                  onFeedback={handleFeedback}
                  feedbackState={message.id ? feedbackByMessageId[message.id] ?? 'idle' : 'idle'}
                />
              ))
            )}
            {sending ? (
              <div className="rounded-3xl bg-slate-950/80 px-5 py-4 text-sm text-slate-400">Thinking…</div>
            ) : null}
            <div ref={bottomRef} />
          </div>

          {ready && messages.length <= 1 ? (
            <div className="border-t border-slate-800 px-4 py-3 sm:px-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Try asking</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {starterPrompts.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => handleStarterClick(item)}
                    className="rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1.5 text-left text-xs text-slate-300 transition hover:border-pink-500/40 hover:text-white sm:text-sm"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="border-t border-slate-800 px-4 py-4 sm:px-6">
            <div className="flex gap-2 sm:gap-3">
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
                disabled={loading}
                className="min-w-0 flex-1 rounded-2xl border border-slate-800 bg-slate-950/90 px-4 py-3 text-slate-100 outline-none transition focus:border-pink-500 disabled:opacity-60"
              />
              <button
                type="button"
                onClick={() => handleSend()}
                disabled={sending || loading || !prompt.trim()}
                className="rounded-2xl bg-pink-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-pink-400 disabled:cursor-not-allowed disabled:opacity-60 sm:px-5"
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
