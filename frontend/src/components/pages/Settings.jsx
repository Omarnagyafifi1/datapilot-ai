import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon, Brain, Key, Shield, ToggleLeft, Save, AlertCircle,
  RefreshCw, BarChart3, Info, CheckCircle2, Unlock,
} from 'lucide-react';
import { api } from '../../lib/api';
import { cn } from '../../lib/utils';
import { PROVIDERS } from '../../lib/constants';

const FEATURES = [
  { key: 'scenario_memory', label: 'Scenario Memory', desc: 'Log SQL failures with lessons learned for future reference.' },
  { key: 'arabic_column_rewrite', label: 'Arabic Column Rewrite', desc: 'Auto-replace English columns with _ar variants for Arabic queries.' },
  { key: 'context_filtering', label: 'Context-Aware Schema Filtering', desc: 'Use LLM to prune irrelevant tables/columns before SQL generation.' },
  { key: 'auto_visualization', label: 'Auto Visualization', desc: 'Automatically generate Plotly charts from query results.' },
  { key: 'human_approval_write', label: 'Human Approval for Writes', desc: 'Require user confirmation before executing INSERT/UPDATE/DELETE.' },
];

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
    success: 'bg-cyber-lime text-black',
  };
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={cn('w-1.5 h-1.5 rounded-full', {
        'bg-cyber-lime': status === 'online' || status === 'success',
        'bg-red-400': status === 'offline',
        'bg-cyber-cyan': status === 'configured',
        'bg-amber-400': status === 'mock',
      })} />
      <span className="text-muted">{label}:</span>
      <span className={cn('px-2 py-0.5 rounded text-[10px] font-bold', colors[status] || colors.loading)}>{status}</span>
    </div>
  );
}

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
    </div>
  );
}

export default function Settings() {
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

  useEffect(() => {
    api.health()
      .then(r => setHealthStatus(r.data?.status === 'ok' ? 'online' : 'offline'))
      .catch(() => setHealthStatus('offline'));

    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    try {
      const resp = await api.settings.get();
      if (resp.data?.success && resp.data?.data) {
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
      if (resp.data?.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        setError(resp.data?.message || 'Save failed');
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

  return (
    <div className="p-12 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-pink mb-4">
          <SettingsIcon size={20} className="animate-spin-slow" />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Configuration Center</span>
        </div>
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
                  placeholder={value && value.includes('•') ? 'Enter new key to change' : `Enter ${provider} API key`}
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
      </div>
    </div>
  );
}