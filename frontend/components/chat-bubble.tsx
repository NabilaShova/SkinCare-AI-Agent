interface ChatBubbleProps {
  role: 'user' | 'assistant' | 'system';
  message: string;
}

export function ChatBubble({ role, message }: ChatBubbleProps) {
  const isAssistant = role === 'assistant';
  return (
    <div className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} py-2`}> 
      <div
        className={`max-w-[80%] rounded-3xl px-5 py-4 text-sm leading-6 shadow-sm ${
          isAssistant ? 'bg-slate-800 text-slate-100' : 'bg-pink-600/10 text-pink-100 border border-pink-500/30'
        }`}
      >
        <p className="font-semibold uppercase tracking-[0.18em] text-[0.6rem] opacity-70">{role === 'assistant' ? 'AI Support' : 'Customer'}</p>
        <p className="mt-3 whitespace-pre-wrap">{message}</p>
      </div>
    </div>
  );
}
