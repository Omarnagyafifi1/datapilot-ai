export const PROVIDERS = [
  { id: 'mock', label: 'Mock LLM', desc: 'Mock provider for testing without API keys.' },
  { id: 'groq', label: 'Groq', desc: 'High-speed open-source models (Llama 3, Mixtral).' },
  { id: 'gemini', label: 'Gemini', desc: 'Google Flash and Pro models.' },
  { id: 'openrouter', label: 'OpenRouter', desc: 'Access to any model through OpenRouter API.' },
  { id: 'azure', label: 'Azure OpenAI', desc: 'Azure OpenAI Service (GPT-4, GPT-4o).' },
];

export const MODELS = {
  groq: [
    { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B' },
    { id: 'llama-3.1-70b-versatile', label: 'Llama 3.1 70B' },
    { id: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
  ],
  gemini: [
    { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
    { id: 'gemini-2.0-pro', label: 'Gemini 2.0 Pro' },
  ],
  openrouter: [
    { id: 'openai/gpt-4o', label: 'GPT-4o' },
    { id: 'anthropic/claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
    { id: 'google/gemini-2.0-flash', label: 'Gemini 2.0 Flash (via OpenRouter)' },
  ],
  mock: [
    { id: 'mock-model', label: 'Mock Model' },
  ],
  azure: [
    { id: 'gpt-4o', label: 'GPT-4o' },
    { id: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { id: 'gpt-35-turbo', label: 'GPT-3.5 Turbo' },
  ],
};
