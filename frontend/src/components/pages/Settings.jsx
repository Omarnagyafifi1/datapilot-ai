import React from 'react';

export function Settings() {
  return (
    <div className="p-12 max-w-4xl mx-auto">
      <h2 className="text-3xl font-extrabold mb-4">Settings</h2>
      <p className="text-muted mb-6">Configure API keys, data source defaults and agent behavior.</p>

      <div className="glass p-6 rounded-2xl border-white/5">
        <h3 className="text-lg font-bold mb-2">API Keys</h3>
        <p className="text-sm text-muted">Configure OpenAI / LLM provider keys in the backend `.env`.</p>
      </div>
    </div>
  );
}

export default Settings;
