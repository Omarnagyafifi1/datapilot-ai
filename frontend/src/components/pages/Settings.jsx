import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, Server, Brain, Shield, Info, ExternalLink, CheckCircle2, Cpu } from 'lucide-react';
import { api } from '../../lib/api';

export function Settings() {
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    api.health()
      .then(resp => setHealthStatus(resp.data?.status === 'ok' ? 'online' : 'offline'))
      .catch(() => setHealthStatus('offline'));
  }, []);

  return (
    <div className="p-12 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-pink mb-4">
          <SettingsIcon size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">System Configuration</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
          SETTINGS<br /><span className="text-muted">.CONFIG</span>
        </h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          System configuration and environment status. API keys and LLM provider settings are managed via the backend <code className="text-cyber-cyan">.env</code> file.
        </p>
      </header>

      <div className="space-y-8">
        {/* System Status */}
        <div className="glass p-6 rounded-2xl border-white/5">
          <h3 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
            <Cpu size={16} className="text-cyber-cyan" /> System Status
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatusCard
              label="Backend API"
              value={healthStatus === 'online' ? 'Online' : healthStatus === 'offline' ? 'Offline' : 'Checking...'}
              status={healthStatus === 'online' ? 'ok' : healthStatus === 'offline' ? 'error' : 'loading'}
            />
            <StatusCard label="Frontend" value="Online" status="ok" />
            <StatusCard label="Database" value="SQLite (Default)" status="ok" />
          </div>
        </div>

        {/* LLM Configuration */}
        <div className="glass p-6 rounded-2xl border-white/5">
          <h3 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
            <Brain size={16} className="text-cyber-lime" /> LLM Configuration
          </h3>
          <p className="text-xs text-muted mb-4 leading-relaxed">
            The AI engine is configured via environment variables in the backend <code className="text-cyber-cyan">.env</code> file. 
            Supported providers: <strong>Groq</strong>, <strong>OpenRouter</strong>, <strong>Gemini</strong>, <strong>OpenAI</strong>.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <EnvItem label="LLM_PROVIDER" desc="Active LLM provider (groq, openrouter, gemini, openai)" />
            <EnvItem label="GROQ_API_KEY" desc="API key for Groq LLM provider" />
            <EnvItem label="OPENROUTER_API_KEY" desc="API key for OpenRouter provider" />
            <EnvItem label="GEMINI_API_KEY" desc="API key for Google Gemini" />
            <EnvItem label="OPENAI_API_KEY" desc="API key for OpenAI" />
            <EnvItem label="ENCRYPTION_KEY" desc="Fernet key for encrypting stored passwords" />
          </div>
        </div>

        {/* Security */}
        <div className="glass p-6 rounded-2xl border-white/5">
          <h3 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
            <Shield size={16} className="text-cyber-pink" /> Security
          </h3>
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
              <CheckCircle2 size={16} className="text-cyber-lime shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-white mb-1">Write Protection</p>
                <p className="text-xs text-muted leading-relaxed">INSERT, UPDATE, and DELETE operations require explicit user approval before execution.</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
              <CheckCircle2 size={16} className="text-cyber-lime shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-white mb-1">SQL Injection Prevention</p>
                <p className="text-xs text-muted leading-relaxed">Dangerous SQL keywords (DROP, ALTER, TRUNCATE, GRANT, REVOKE, EXEC) are blocked at the agent level.</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
              <CheckCircle2 size={16} className="text-cyber-lime shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-white mb-1">Password Encryption</p>
                <p className="text-xs text-muted leading-relaxed">Database passwords are encrypted with Fernet (AES-128-CBC) before storage.</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
              <CheckCircle2 size={16} className="text-cyber-lime shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-white mb-1">Rate Limiting</p>
                <p className="text-xs text-muted leading-relaxed">API endpoints are rate-limited to 120 requests per 60 seconds per client.</p>
              </div>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="glass p-6 rounded-2xl border-white/5">
          <h3 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
            <Info size={16} className="text-cyber-cyan" /> About
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <AboutItem label="Version" value="1.0.0" />
            <AboutItem label="Frontend" value="React + Vite" />
            <AboutItem label="Backend" value="FastAPI" />
            <AboutItem label="AI Engine" value="LangGraph" />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusCard({ label, value, status }) {
  const colors = {
    ok: 'text-cyber-lime',
    error: 'text-red-400',
    loading: 'text-amber-400',
  };
  return (
    <div className="p-4 bg-white/[0.02] border border-white/5 rounded-xl">
      <p className="text-[10px] font-mono font-bold text-muted uppercase tracking-widest mb-2">{label}</p>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${status === 'ok' ? 'bg-cyber-lime' : status === 'error' ? 'bg-red-400' : 'bg-amber-400'} ${status === 'ok' ? 'animate-pulse' : ''}`} />
        <span className={`text-sm font-bold ${colors[status]}`}>{value}</span>
      </div>
    </div>
  );
}

function EnvItem({ label, desc }) {
  return (
    <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl">
      <code className="text-xs font-mono text-cyber-cyan">{label}</code>
      <p className="text-[10px] text-muted mt-1">{desc}</p>
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

export default Settings;
