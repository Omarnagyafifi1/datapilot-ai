<<<<<<< HEAD
import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, Server, Brain, Shield, Sliders, Monitor, CheckCircle, Save } from 'lucide-react';
=======
import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon, Brain, Key, Server, Shield, Info,
  CheckCircle2, Cpu, Eye, ToggleLeft, Save, AlertCircle,
  RefreshCw, Database, BarChart3, Globe, Unlock,
} from 'lucide-react';
>>>>>>> main
import { api } from '../../lib/api';
import { cn } from '../../lib/utils';

const PROVIDERS = [
  { id: 'litellm', label: 'LiteLLM (Latency Router)', desc: 'Dynamically routes to the fastest model among your provided keys.' },
  { id: 'groq', label: 'Groq', desc: 'Fast inference with Llama/Mixtral models.' },
  { id: 'openrouter', label: 'OpenRouter', desc: 'Unified API for 200+ models.' },
  { id: 'gemini', label: 'Google Gemini', desc: 'Google\'s Gemini models.' },
  { id: 'openai', label: 'OpenAI', desc: 'GPT-4 / GPT-3.5 models.' },
  { id: 'mock', label: 'Mock (No LLM)', desc: 'Uses pre-defined responses for testing, no API key needed.' },
];

const FEATURES = [
  { key: 'scenario_memory', label: 'Scenario Memory', desc: 'Log SQL failures with lessons learned for future reference.' },
  { key: 'arabic_column_rewrite', label: 'Arabic Column Rewrite', desc: 'Auto-replace English columns with _ar variants for Arabic queries.' },
  { key: 'context_filtering', label: 'Context-Aware Schema Filtering', desc: 'Use LLM to prune irrelevant tables/columns before SQL generation.' },
  { key: 'auto_visualization', label: 'Auto Visualization', desc: 'Automatically generate Plotly charts from query results.' },
  { key: 'human_approval_write', label: 'Human Approval for Writes', desc: 'Require user confirmation before executing INSERT/UPDATE/DELETE.' },
];

<<<<<<< HEAD
const PROVIDER_MODELS = {
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o (Recommended)' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
    { id: 'o1-preview', name: 'o1 Preview' },
    { id: 'o1-mini', name: 'o1 Mini' }
  ],
  anthropic: [
    { id: 'claude-3-5-sonnet-latest', name: 'Claude 3.5 Sonnet (Recommended)' },
    { id: 'claude-3-5-haiku-latest', name: 'Claude 3.5 Haiku' },
    { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus' }
  ],
  gemini: [
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash (Recommended)' },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro' },
    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' }
  ],
  groq: [
    { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B (Recommended)' },
    { id: 'mixtral-8x7b-32768', name: 'Mixtral 8x7B' },
    { id: 'gemma2-9b-it', name: 'Gemma 2 9B' }
  ],
  deepseek: [
    { id: 'deepseek-chat', name: 'DeepSeek-V3 (Recommended)' },
    { id: 'deepseek-coder', name: 'DeepSeek Coder' }
  ],
  openrouter: [
    { id: 'meta-llama/llama-3.3-70b-instruct', name: 'Llama 3.3 70B via OpenRouter' },
    { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet via OpenRouter' },
    { id: 'google/gemini-2.5-pro', name: 'Gemini 2.5 Pro via OpenRouter' }
  ],
  together: [
    { id: 'togethercomputer/llama-2-70b-chat', name: 'Llama 2 70B Chat' },
    { id: 'mistralai/Mixtral-8x7B-Instruct-v0.1', name: 'Mixtral 8x7B Instruct' }
  ],
  ollama: [
    { id: 'llama3', name: 'Llama 3 (Local)' },
    { id: 'mistral', name: 'Mistral (Local)' },
    { id: 'phi3', name: 'Phi-3 (Local)' }
  ]
};

export function Settings({ themeMode, onChangeTheme }) {
  const [activeTab, setActiveTab] = useState('providers');
  const [healthStatus, setHealthStatus] = useState(null);
  const [savedStatus, setSavedStatus] = useState(false);

  // Settings state
  const [apiKeys, setApiKeys] = useState({
    openai: '',
    anthropic: '',
    gemini: '',
    groq: '',
    deepseek: '',
    openrouter: '',
    together: '',
    ollama: ''
  });

  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');

  const [appPrefs, setAppPrefs] = useState({
    interfaceScale: 'medium',
    autoExecute: false,
    enterToSend: true,
    streamResponse: true
  });

  const [advanced, setAdvanced] = useState({
    temperature: 0.2,
    maxTokens: 2048,
    developerMode: false
  });

  // Load settings from backend on mount
=======
export function Settings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  const [llmProvider, setLlmProvider] = useState('mock');
  const [apiKeys, setApiKeys] = useState({ groq: '', openrouter: '', gemini: '', openai: '' });
  const [features, setFeatures] = useState({});
  const [vizConfig, setVizConfig] = useState({ default_chart_type: 'auto', max_bars: 20, theme: 'dark' });

>>>>>>> main
  useEffect(() => {
    api.health()
      .then(r => setHealthStatus(r.data?.status === 'ok' ? 'online' : 'offline'))
      .catch(() => setHealthStatus('offline'));
<<<<<<< HEAD

    // Load LLM settings from backend
    api.settings.get()
      .then(resp => {
        if (resp.data?.success && resp.data?.data) {
          const settings = resp.data.data;
          setSelectedProvider(settings.provider || 'groq');
          setSelectedModel(settings.model || 'llama-3.3-70b-versatile');
          setAdvanced(prev => ({
            ...prev,
            temperature: settings.temperature ?? prev.temperature,
            maxTokens: settings.max_tokens ?? prev.maxTokens,
          }));
        }
      })
      .catch(err => {
        console.warn('Could not load LLM settings from backend, using localStorage fallback:', err);
        // Fallback to localStorage if backend unavailable
        const storedApiKeys = {
          openai: localStorage.getItem('dp_key_openai') || '',
          anthropic: localStorage.getItem('dp_key_anthropic') || '',
          gemini: localStorage.getItem('dp_key_gemini') || '',
          groq: localStorage.getItem('dp_key_groq') || '',
          deepseek: localStorage.getItem('dp_key_deepseek') || '',
          openrouter: localStorage.getItem('dp_key_openrouter') || '',
          together: localStorage.getItem('dp_key_together') || '',
          ollama: localStorage.getItem('dp_key_ollama') || ''
        };
        const storedProvider = localStorage.getItem('dp_provider') || 'groq';
        const storedModel = localStorage.getItem('dp_model') || 'llama-3.3-70b-versatile';
        const storedTemp = parseFloat(localStorage.getItem('dp_temperature') || '0.2');
        const storedMaxTokens = parseInt(localStorage.getItem('dp_max_tokens') || '2048');
        
        setApiKeys(storedApiKeys);
        setSelectedProvider(storedProvider);
        setSelectedModel(storedModel);
        setAdvanced(prev => ({
          ...prev,
          temperature: storedTemp,
          maxTokens: storedMaxTokens
        }));
      });
  }, []);

  // Update default model if provider changes and current model is not compatible
  useEffect(() => {
    const models = PROVIDER_MODELS[selectedProvider] || [];
    const isCompatible = models.some(m => m.id === selectedModel);
    if (!isCompatible && models.length > 0) {
      setSelectedModel(models[0].id);
    }
  }, [selectedProvider, selectedModel]);

  const handleSave = async () => {
    // Save API keys to localStorage (for frontend use)
    Object.entries(apiKeys).forEach(([provider, key]) => {
      localStorage.setItem(`dp_key_${provider}`, key);
    });

    // Save active provider and model
    localStorage.setItem('dp_provider', selectedProvider);
    localStorage.setItem('dp_model', selectedModel);

    // Save app prefs
    localStorage.setItem('dp_scale', appPrefs.interfaceScale);
    localStorage.setItem('dp_auto_execute', String(appPrefs.autoExecute));
    localStorage.setItem('dp_enter_to_send', String(appPrefs.enterToSend));
    localStorage.setItem('dp_stream_response', String(appPrefs.streamResponse));

    // Save advanced settings
    localStorage.setItem('dp_temperature', String(advanced.temperature));
    localStorage.setItem('dp_max_tokens', String(advanced.maxTokens));
    localStorage.setItem('dp_dev_mode', String(advanced.developerMode));

    // Save LLM settings to backend
    try {
      await api.settings.update({
        provider: selectedProvider,
        model: selectedModel,
        temperature: advanced.temperature,
        maxTokens: advanced.maxTokens,
        apiKeys: apiKeys,
      });
    } catch (err) {
      console.warn('Could not save LLM settings to backend:', err);
    }

    setSavedStatus(true);
    setTimeout(() => setSavedStatus(false), 2000);
  };
=======
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    try {
      const resp = await api.settings.get();
      if (resp.data.success) {
        const s = resp.data.data;
        setSettings(s);
        setLlmProvider(s.llm_provider || 'mock');
        setApiKeys(prev => ({ ...prev, ...s.api_keys }));
        setFeatures(s.features || {});
        setVizConfig(s.visualization || { default_chart_type: 'auto', max_bars: 20, theme: 'dark' });
      }
    } catch (err) {
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  }

  async function saveSettings() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const payload = {
        llm_provider: llmProvider,
        api_keys: Object.fromEntries(Object.entries(apiKeys).filter(([, v]) => v)),
        visualization: vizConfig,
        features,
      };
      const resp = await api.settings.update(payload);
      if (resp.data.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        setError(resp.data.message || 'Save failed');
      }
    } catch (err) {
      setError('Failed to save settings. Check backend connection.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-12 max-w-5xl mx-auto flex items-center justify-center min-h-[60vh]">
        <div className="text-muted text-sm animate-pulse">Loading settings...</div>
      </div>
    );
  }
>>>>>>> main

  return (
    <div className="p-12 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="mb-12 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-cyber-pink mb-4">
            <SettingsIcon size={20} className="animate-spin-slow" />
            <span className="text-xs font-mono font-bold uppercase tracking-widest">Configuration Center</span>
          </div>
          <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
            SETTINGS<br /><span className="text-muted">.CONFIG</span>
          </h2>
          <p className="text-muted max-w-xl text-sm leading-relaxed">
            Customize AI engine routing, system access credentials, user interface themes, and advanced parameters.
          </p>
        </div>
<<<<<<< HEAD

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-6 py-3 bg-cyber-lime text-background font-mono font-bold text-xs uppercase tracking-widest rounded-xl hover:brightness-110 active:scale-95 transition-all shadow-glow-lime/20 shadow-lg"
        >
          {savedStatus ? (
            <>
              <CheckCircle size={14} /> Saved Successfully
            </>
          ) : (
            <>
              <Save size={14} /> Save Configuration
            </>
          )}
        </button>
      </header>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Side Tab Navigation */}
        <aside className="w-full md:w-64 flex flex-col gap-2">
          <TabButton active={activeTab === 'providers'} onClick={() => setActiveTab('providers')} icon={<Brain size={16} />} label="AI Providers" desc="API Keys & Model Selection" />
          <TabButton active={activeTab === 'application'} onClick={() => setActiveTab('application')} icon={<Monitor size={16} />} label="Application" desc="Theme & Chat Preferences" />
          <TabButton active={activeTab === 'advanced'} onClick={() => setActiveTab('advanced')} icon={<Sliders size={16} />} label="Advanced" desc="Developer & Temperature Options" />
          <TabButton active={activeTab === 'status'} onClick={() => setActiveTab('status')} icon={<Server size={16} />} label="System Status" desc="Network & Database Health" />
        </aside>

        {/* Right Side Settings Panel */}
        <main className="flex-1 glass p-8 rounded-2xl border-border bg-card/60 backdrop-blur-xl">
          {activeTab === 'providers' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-2">Provider & Model Selection</h3>
                <p className="text-xs text-muted">Select the neural provider and corresponding LLM target for processing database queries.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
                <div className="space-y-2">
                  <label className="text-xs font-mono font-bold text-muted uppercase">Default Provider</label>
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="w-full bg-foreground/5 border border-border rounded-xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-cyber-cyan transition-colors"
                  >
                    <option value="groq">Groq</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="deepseek">DeepSeek</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="together">Together AI</option>
                    <option value="ollama">Ollama (Local)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-mono font-bold text-muted uppercase">Default Model</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full bg-foreground/5 border border-border rounded-xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-cyber-cyan transition-colors"
                  >
                    {(PROVIDER_MODELS[selectedProvider] || []).map((model) => (
                      <option key={model.id} value={model.id}>{model.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="border-t border-border pt-6 mt-6">
                <h4 className="text-sm font-mono font-bold text-foreground/80 uppercase mb-4 flex items-center gap-2">
                  <Key size={14} className="text-cyber-pink" /> API Credentials
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.keys(apiKeys).map((provider) => (
                    <div key={provider} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-muted capitalize">{provider} API Key</span>
                      </div>
                      <input
                        type="password"
                        placeholder="••••••••••••••••••••"
                        value={apiKeys[provider]}
                        onChange={(e) => setApiKeys({ ...apiKeys, [provider]: e.target.value })}
                        className="w-full bg-foreground/5 border border-border rounded-xl px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-cyber-cyan transition-colors font-mono"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'application' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-2">Application Preferences</h3>
                <p className="text-xs text-muted">Adjust themes, interface layouts, and core chat settings to optimize your workflow.</p>
              </div>

              <div className="space-y-4 pt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-bold text-foreground/60 uppercase">Theme Preference</label>
                    <select
                      value={themeMode || 'dark'}
                      onChange={(e) => onChangeTheme(e.target.value)}
                      className="w-full bg-foreground/5 border border-border rounded-xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-cyber-cyan transition-colors"
                    >
                      <option value="dark" className="bg-card text-foreground">Layered Dark Mode</option>
                      <option value="light" className="bg-card text-foreground">Clean Light Mode</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-mono font-bold text-foreground/60 uppercase">Interface Scale</label>
                    <select
                      value={appPrefs.interfaceScale}
                      onChange={(e) => setAppPrefs({ ...appPrefs, interfaceScale: e.target.value })}
                      className="w-full bg-foreground/5 border border-border rounded-xl px-4 py-3 text-sm text-foreground focus:outline-none focus:border-cyber-cyan transition-colors"
                    >
                      <option value="small" className="bg-card text-foreground">Compact</option>
                      <option value="medium" className="bg-card text-foreground">Default (Medium)</option>
                      <option value="large" className="bg-card text-foreground">Spacious</option>
                    </select>
                  </div>
                </div>

                <div className="border-t border-border pt-6 mt-6 space-y-4">
                  <h4 className="text-sm font-mono font-bold text-foreground/80 uppercase">Conversational Behavior</h4>
                  
                  <ToggleItem
                    label="Auto-Execute Generated SQL"
                    desc="Automatically execute SELECT SQL queries against the database without requiring manual approval clicks."
                    checked={appPrefs.autoExecute}
                    onChange={(checked) => setAppPrefs({ ...appPrefs, autoExecute: checked })}
                  />

                  <ToggleItem
                    label="Simulate Response Streaming"
                    desc="Simulate typing streams in the chat logs instead of instant rendering."
                    checked={appPrefs.streamResponse}
                    onChange={(checked) => setAppPrefs({ ...appPrefs, streamResponse: checked })}
                  />

                  <ToggleItem
                    label="Enter to Send Messages"
                    desc="Press Enter key to submit prompts. Shift + Enter to add newline."
                    checked={appPrefs.enterToSend}
                    onChange={(checked) => setAppPrefs({ ...appPrefs, enterToSend: checked })}
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-2">Advanced Engine Tuning</h3>
                <p className="text-xs text-muted">Fine-tune system parameters, token budgets, and override server configurations.</p>
              </div>

              <div className="space-y-6 pt-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-muted uppercase">LLM Temperature</span>
                    <span className="text-xs font-mono font-bold text-cyber-cyan">{advanced.temperature}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={advanced.temperature}
                    onChange={(e) => setAdvanced({ ...advanced, temperature: parseFloat(e.target.value) })}
                    className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-cyber-cyan"
                  />
                  <p className="text-[10px] text-muted">Lower values generate deterministic SQL; higher values introduce more creative explanations.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-border">
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-bold text-muted uppercase">Max Output Tokens</label>
                    <input
                      type="number"
                      value={advanced.maxTokens}
                      onChange={(e) => setAdvanced({ ...advanced, maxTokens: parseInt(e.target.value) })}
                      className="w-full bg-foreground/5 border border-border rounded-xl px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-cyber-cyan transition-colors font-mono"
                    />
                  </div>

                  <div className="flex flex-col justify-center space-y-2">
                    <ToggleItem
                      label="Developer Console Mode"
                      desc="Expose latency charts, compiler traces, and graph checkpointers."
                      checked={advanced.developerMode}
                      onChange={(checked) => setAdvanced({ ...advanced, developerMode: checked })}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'status' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-2">System Diagnostics</h3>
                <p className="text-xs text-muted">View connectivity stats and network health diagnostics.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                <StatusItem
                  title="Backend API Engine"
                  value={healthStatus === 'online' ? 'Online' : healthStatus === 'offline' ? 'Offline' : 'Diagnosing...'}
                  status={healthStatus === 'online' ? 'success' : 'error'}
                />
                <StatusItem title="Database Connection" value="Connected" status="success" />
                <StatusItem title="Checkpointer Cache" value="Active (In-Memory)" status="success" />
              </div>

              <div className="border-t border-border pt-6 mt-6">
                <h4 className="text-sm font-mono font-bold text-foreground/80 uppercase mb-4 flex items-center gap-2">
                  <Shield size={14} className="text-cyber-lime" /> Platform Safety Controls
                </h4>
                <div className="space-y-3">
                  <SafetyBadge label="Write Protection Status" desc="INSERT, UPDATE, DELETE queries require manual permission locks." />
                  <SafetyBadge label="SQL Sanity Check" desc="Blocks DROP, ALTER, TRUNCATE statements automatically." />
                  <SafetyBadge label="Database Password Storage" desc="All stored DB credentials are encrypted with AES-128-CBC." />
                </div>
              </div>
            </div>
          )}
        </main>
=======
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
          SETTINGS<br /><span className="text-muted">.CONFIG</span>
        </h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Configure LLM providers, API keys, feature toggles, and visualization preferences.
          Changes are saved to the backend and take effect immediately.
        </p>
      </header>

      <div className="space-y-8">
        {/* Status Bar */}
        <div className="flex items-center gap-4 flex-wrap">
          <StatusBadge label="Backend" status={healthStatus} />
          <StatusBadge label="Provider" status={llmProvider === 'mock' ? 'mock' : 'configured'} />
          {saved && <span className="text-xs text-cyber-lime flex items-center gap-1"><CheckCircle2 size={12} /> Saved</span>}
          {error && <span className="text-xs text-red-400 flex items-center gap-1"><AlertCircle size={12} /> {error}</span>}
        </div>

        {/* LLM Provider */}
        <Section icon={<Brain size={16} />} title="LLM Provider" color="text-cyber-lime">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
            {PROVIDERS.map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => setLlmProvider(p.id)}
                className={cn(
                  'p-4 rounded-xl border text-left transition-all',
                  llmProvider === p.id
                    ? 'bg-cyber-lime/10 border-cyber-lime/40 text-white'
                    : 'bg-white/[0.02] border-white/5 text-muted hover:border-white/20',
                )}
              >
                <div className="text-sm font-bold mb-1">{p.label}</div>
                <div className="text-[10px] leading-relaxed opacity-70">{p.desc}</div>
              </button>
            ))}
          </div>
        </Section>

        {/* API Keys */}
        <Section icon={<Key size={16} />} title="API Keys" color="text-cyber-cyan">
          <p className="text-xs text-muted mb-4">API keys are stored encrypted in a local file. Keys are masked after saving.</p>
          <div className="space-y-3 max-w-xl">
            {Object.entries(apiKeys).map(([provider, value]) => (
              <div key={provider}>
                <label className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-widest mb-1 block">
                  {provider.toUpperCase()}_API_KEY
                </label>
                <input
                  type="password"
                  value={value}
                  onChange={e => setApiKeys(prev => ({ ...prev, [provider]: e.target.value }))}
                  placeholder={value && value.includes('••') ? 'Enter new key to change' : `Enter ${provider} API key`}
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white font-mono placeholder:text-white/20 focus:outline-none focus:border-cyber-cyan/40 transition-colors"
                />
              </div>
            ))}
          </div>
        </Section>

        {/* Feature Toggles */}
        <Section icon={<ToggleLeft size={16} />} title="Feature Toggles" color="text-amber-400">
          <div className="space-y-3 max-w-xl">
            {FEATURES.map(f => (
              <div key={f.key} className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                <button
                  type="button"
                  onClick={() => setFeatures(prev => ({ ...prev, [f.key]: !prev[f.key] }))}
                  className={cn(
                    'w-10 h-6 rounded-full transition-colors shrink-0 mt-0.5 relative',
                    features[f.key] ? 'bg-cyber-lime/30' : 'bg-white/10',
                  )}
                >
                  <div className={cn(
                    'w-4 h-4 rounded-full absolute top-1 transition-all',
                    features[f.key] ? 'bg-cyber-lime left-[22px]' : 'bg-white/40 left-1',
                  )} />
                </button>
                <div>
                  <p className="text-xs font-bold text-white mb-1">{f.label}</p>
                  <p className="text-[10px] text-muted leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Visualization */}
        <Section icon={<BarChart3 size={16} />} title="Visualization" color="text-purple-400">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-xl">
            <div>
              <label className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-widest block mb-1">Default Chart</label>
              <select
                value={vizConfig.default_chart_type}
                onChange={e => setVizConfig(prev => ({ ...prev, default_chart_type: e.target.value }))}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-purple-400/40"
              >
                <option value="auto">Auto-detect</option>
                <option value="bar">Bar Chart</option>
                <option value="line">Line Chart</option>
                <option value="pie">Pie Chart</option>
                <option value="scatter">Scatter Plot</option>
                <option value="histogram">Histogram</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-widest block mb-1">Max Bars</label>
              <input
                type="number"
                min={5}
                max={50}
                value={vizConfig.max_bars}
                onChange={e => setVizConfig(prev => ({ ...prev, max_bars: Number(e.target.value) }))}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-purple-400/40"
              />
            </div>
            <div>
              <label className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-widest block mb-1">Theme</label>
              <select
                value={vizConfig.theme}
                onChange={e => setVizConfig(prev => ({ ...prev, theme: e.target.value }))}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-purple-400/40"
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="plotly_white">Plotly White</option>
              </select>
            </div>
          </div>
        </Section>

        {/* Save */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={saveSettings}
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-3 bg-cyber-cyan/20 border border-cyber-cyan/30 rounded-xl text-sm font-bold text-white hover:bg-cyber-cyan/30 transition-all disabled:opacity-40"
          >
            {saving ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            type="button"
            onClick={loadSettings}
            className="inline-flex items-center gap-2 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-xs text-muted hover:text-white transition-all"
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {/* Security Info */}
        <Section icon={<Unlock size={16} />} title="Security" color="text-cyber-pink">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SecurityCard icon={<CheckCircle2 size={16} className="text-cyber-lime" />} title="Write Protection" desc="INSERT, UPDATE, DELETE require user approval." />
            <SecurityCard icon={<CheckCircle2 size={16} className="text-cyber-lime" />} title="SQL Injection Prevention" desc="DROP, ALTER, TRUNCATE, GRANT are blocked." />
            <SecurityCard icon={<CheckCircle2 size={16} className="text-cyber-lime" />} title="Password Encryption" desc="Database passwords encrypted with Fernet AES-128." />
            <SecurityCard icon={<CheckCircle2 size={16} className="text-cyber-lime" />} title="API Key Storage" desc="Keys stored locally in settings.json, never exposed." />
          </div>
        </Section>

        {/* About */}
        <Section icon={<Info size={16} />} title="About" color="text-cyber-cyan">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <AboutItem label="Version" value="1.0.0" />
            <AboutItem label="Frontend" value="React + Vite" />
            <AboutItem label="Backend" value="FastAPI" />
            <AboutItem label="Engine" value="LangGraph" />
          </div>
        </Section>
>>>>>>> main
      </div>
    </div>
  );
}

<<<<<<< HEAD
function TabButton({ active, icon, label, desc, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-start gap-4 p-4 rounded-xl text-left transition-all border ${
        active 
          ? 'bg-cyber-cyan/10 border-cyber-cyan/30 text-foreground' 
          : 'bg-transparent border-transparent text-muted hover:text-foreground hover:bg-foreground/[0.03]'
      }`}
    >
      <div className={`p-2 rounded-lg ${active ? 'bg-cyber-cyan/20 text-cyber-cyan' : 'bg-white/5 text-muted'}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm font-bold">{label}</p>
        <p className="text-[10px] text-muted mt-0.5">{desc}</p>
      </div>
    </button>
  );
}

function ToggleItem({ label, desc, checked, onChange }) {
  return (
    <div className="flex items-start justify-between gap-4 p-4 bg-foreground/[0.03] border border-border rounded-xl hover:bg-foreground/[0.05] transition-colors">
      <div className="space-y-1">
        <p className="text-xs font-bold text-foreground">{label}</p>
        <p className="text-[10px] text-muted max-w-md leading-relaxed">{desc}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`w-10 h-6 rounded-full transition-colors flex items-center p-0.5 cursor-pointer border ${
          checked ? 'bg-cyber-cyan border-cyber-cyan' : 'bg-foreground/10 border-border'
        }`}
      >
        <div className={`w-4.5 h-4.5 rounded-full bg-background transition-transform transform ${checked ? 'translate-x-4' : 'translate-x-0'}`} />
      </button>
    </div>
  );
}

function StatusItem({ title, value, status }) {
  return (
    <div className="p-4 bg-foreground/[0.03] border border-border rounded-xl text-left">
      <p className="text-[10px] font-mono font-bold text-muted uppercase tracking-widest mb-2">{title}</p>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${status === 'success' ? 'bg-cyber-lime' : 'bg-red-400'} animate-pulse`} />
        <span className={`text-sm font-bold ${status === 'success' ? 'text-cyber-lime' : 'text-red-400'}`}>{value}</span>
      </div>
=======
function Section({ icon, title, color, children }) {
  return (
    <div className="glass p-6 rounded-2xl border-white/5">
      <h3 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
        <span className={color}>{icon}</span> {title}
      </h3>
      {children}
    </div>
  );
}

function StatusBadge({ label, status }) {
  const colors = {
    online: 'bg-cyber-lime text-black',
    offline: 'bg-red-400/20 text-red-400',
    configured: 'bg-cyber-cyan/20 text-cyber-cyan',
    mock: 'bg-amber-400/20 text-amber-400',
    loading: 'bg-white/10 text-muted',
  };
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={cn('w-1.5 h-1.5 rounded-full', {
        'bg-cyber-lime': status === 'online',
        'bg-red-400': status === 'offline',
        'bg-cyber-cyan': status === 'configured',
        'bg-amber-400': status === 'mock',
      })} />
      <span className="text-muted">{label}:</span>
      <span className={cn('px-2 py-0.5 rounded text-[10px] font-bold', colors[status] || colors.loading)}>{status}</span>
>>>>>>> main
    </div>
  );
}

<<<<<<< HEAD
function SafetyBadge({ label, desc }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-foreground/[0.02] border border-border rounded-lg text-left">
      <CheckCircle size={14} className="text-cyber-lime mt-0.5 shrink-0" />
      <div>
        <p className="text-xs font-bold text-foreground/95">{label}</p>
        <p className="text-[10px] text-muted leading-relaxed mt-0.5">{desc}</p>
      </div>
=======
function SecurityCard({ icon, title, desc }) {
  return (
    <div className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
      <span className="shrink-0 mt-0.5">{icon}</span>
      <div>
        <p className="text-xs font-bold text-white mb-1">{title}</p>
        <p className="text-xs text-muted leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function AboutItem({ label, value }) {
  return (
    <div className="p-4 bg-white/[0.02] border border-white/5 rounded-xl text-center">
      <p className="text-[10px] font-mono font-bold text-muted uppercase tracking-widest mb-2">{label}</p>
      <p className="text-sm font-bold text-white">{value}</p>
>>>>>>> main
    </div>
  );
}

export default Settings;
