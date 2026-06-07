export type StarterPromptCategory = 'skin' | 'hair' | 'ingredients' | 'store';

export interface StarterPrompt {
  label: string;
  prompt: string;
  category: StarterPromptCategory;
}

export const STARTER_PROMPT_CATEGORIES: Record<
  StarterPromptCategory,
  { title: string; accent: string }
> = {
  skin: { title: 'Skincare', accent: 'text-pink-300' },
  hair: { title: 'Hair care', accent: 'text-violet-300' },
  ingredients: { title: 'Ingredients', accent: 'text-amber-300' },
  store: { title: 'Orders & policies', accent: 'text-sky-300' },
};

export const CHAT_STARTER_PROMPTS: StarterPrompt[] = [
  {
    category: 'skin',
    label: 'Oily acne skin',
    prompt: 'I have oily, acne-prone skin. What products help with prevention?',
  },
  {
    category: 'skin',
    label: 'Dry skin routine',
    prompt: 'I have dry sensitive skin — suggest a simple morning routine.',
  },
  {
    category: 'skin',
    label: 'Dark spots',
    prompt: 'What products do you recommend for dark spots and uneven tone?',
  },
  {
    category: 'hair',
    label: 'Hair fall',
    prompt: 'What shampoo helps with hair fall in humid weather?',
  },
  {
    category: 'hair',
    label: 'Dandruff',
    prompt: 'I have dandruff and an itchy scalp — what should I use?',
  },
  {
    category: 'hair',
    label: 'Frizzy curls',
    prompt: 'Recommend products for frizzy curly hair.',
  },
  {
    category: 'ingredients',
    label: 'Niacinamide + Vitamin C',
    prompt: 'Can I use Niacinamide with Vitamin C?',
  },
  {
    category: 'ingredients',
    label: 'Retinol + BHA',
    prompt: 'Can I use retinol and salicylic acid together?',
  },
  {
    category: 'store',
    label: 'Shipping',
    prompt: 'Do you ship internationally?',
  },
  {
    category: 'store',
    label: 'Returns',
    prompt: 'What is your return policy?',
  },
];

export const CHAT_INPUT_PLACEHOLDER =
  'Ask about skincare, hair care, ingredients, shipping, or your order...';
