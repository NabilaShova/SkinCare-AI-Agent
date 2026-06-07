'use client';

import {
  CHAT_STARTER_PROMPTS,
  STARTER_PROMPT_CATEGORIES,
  type StarterPromptCategory,
} from '@/lib/chat-starter-prompts';

interface ChatStarterPromptsProps {
  onSelect: (prompt: string) => void;
  compact?: boolean;
}

const CATEGORY_ORDER: StarterPromptCategory[] = ['skin', 'hair', 'ingredients', 'store'];

export function ChatStarterPrompts({ onSelect, compact = false }: ChatStarterPromptsProps) {
  return (
    <div className="space-y-3">
      <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Try asking</p>
      {CATEGORY_ORDER.map((category) => {
        const prompts = CHAT_STARTER_PROMPTS.filter((item) => item.category === category);
        if (!prompts.length) return null;
        const meta = STARTER_PROMPT_CATEGORIES[category];
        return (
          <div key={category}>
            <p className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${meta.accent}`}>
              {meta.title}
            </p>
            <div className={`mt-1.5 flex flex-wrap gap-2 ${compact ? '' : ''}`}>
              {prompts.map((item) => (
                <button
                  key={item.prompt}
                  type="button"
                  onClick={() => onSelect(item.prompt)}
                  title={item.prompt}
                  className="rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1.5 text-left text-xs text-slate-300 transition hover:border-pink-500/40 hover:text-white sm:text-sm"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
