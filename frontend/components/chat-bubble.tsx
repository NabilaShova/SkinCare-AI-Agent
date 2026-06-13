import { Fragment } from 'react';

interface ChatBubbleProps {
  role: 'user' | 'assistant' | 'system';
  message: string;
  messageId?: number;
  showFeedback?: boolean;
  onFeedback?: (messageId: number, helpful: boolean) => void;
  feedbackState?: 'idle' | 'sending' | 'helpful' | 'not_helpful';
}

const MARKDOWN_LINK_PATTERN = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;

function renderMessageContent(message: string) {
  const nodes: Array<string | JSX.Element> = [];
  let lastIndex = 0;

  for (const match of message.matchAll(MARKDOWN_LINK_PATTERN)) {
    const [fullMatch, label, href] = match;
    const index = match.index ?? 0;

    if (index > lastIndex) {
      nodes.push(message.slice(lastIndex, index));
    }

    nodes.push(
      <a
        key={`${index}-${href}`}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-pink-300 underline decoration-pink-400/60 underline-offset-2 transition hover:text-pink-200"
      >
        {label}
      </a>,
    );

    lastIndex = index + fullMatch.length;
  }

  if (lastIndex < message.length) {
    nodes.push(message.slice(lastIndex));
  }

  if (nodes.length === 0) {
    return message;
  }

  return nodes.map((node, index) => (
    <Fragment key={typeof node === 'string' ? `text-${index}` : `link-${index}`}>{node}</Fragment>
  ));
}

export function ChatBubble({
  role,
  message,
  messageId,
  showFeedback = false,
  onFeedback,
  feedbackState = 'idle',
}: ChatBubbleProps) {
  const isAssistant = role === 'assistant';
  return (
    <div className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} py-2`}>
      <div
        className={`max-w-[80%] rounded-3xl px-5 py-4 text-sm leading-6 shadow-sm ${
          isAssistant ? 'bg-slate-800 text-slate-100' : 'bg-pink-600/10 text-pink-100 border border-pink-500/30'
        }`}
      >
        <p className="font-semibold uppercase tracking-[0.18em] text-[0.6rem] opacity-70">
          {role === 'assistant' ? 'AI Support' : 'Customer'}
        </p>
        <p className="mt-3 whitespace-pre-wrap">{renderMessageContent(message)}</p>
        {showFeedback && messageId && onFeedback ? (
          <div className="mt-4 flex items-center gap-2 border-t border-slate-700/80 pt-3">
            <span className="text-[0.65rem] uppercase tracking-[0.18em] text-slate-500">Helpful?</span>
            <button
              type="button"
              disabled={feedbackState === 'sending' || feedbackState !== 'idle'}
              onClick={() => onFeedback(messageId, true)}
              className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-300 transition hover:border-emerald-500/50 hover:text-emerald-300 disabled:opacity-50"
            >
              {feedbackState === 'helpful' ? 'Saved' : 'Yes'}
            </button>
            <button
              type="button"
              disabled={feedbackState === 'sending' || feedbackState !== 'idle'}
              onClick={() => onFeedback(messageId, false)}
              className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-300 transition hover:border-red-500/50 hover:text-red-300 disabled:opacity-50"
            >
              {feedbackState === 'not_helpful' ? 'Noted' : 'No'}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
