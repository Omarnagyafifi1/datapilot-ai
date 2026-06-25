import React, { useState, useEffect } from 'react';
import { Database, Plus, Trash2, Globe, Server, Shield, AlertCircle, Loader2, Cpu, Zap } from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '../lib/utils';
import { COPY } from '../lib/copy';

export function DataSourceManager({ onUpdate }) {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    db_type: 'postgresql',
    host: '',
    port: 5432,
    db_name: '',
    username: '',
    password: ''
  });

  const fetchSources = async () => {
    try {
      setLoading(true);
      const resp = await api.datasources.list();
      if (resp.data.success) {
        setSources(resp.data.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleConnect = async (e) => {
    e.preventDefault();
    setConnecting(true);
    setError(null);
    try {
      const resp = await api.datasources.connect(formData);
      if (resp.data.success) {
        fetchSources();
        onUpdate();
        setFormData({
          name: '',
          db_type: 'postgresql',
          host: '',
          port: 5432,
          db_name: '',
          username: '',
          password: ''
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Connection failed. Check connection details.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Decommission this data node?")) return;
    try {
      await api.datasources.delete(id);
      fetchSources();
      onUpdate();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-cyan mb-4">
          <Database size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Network Orchestration</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">DATA_NODES<br /><span className="text-muted">.CONFIG</span></h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Manage your distributed data relays. Stabilize connections between the core engine and your heterogeneous sources.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div className="lg:col-span-1">
          <div className="glass p-8 rounded-2xl border-white/5 sticky top-8">
            <h3 className="text-sm font-mono font-bold text-white uppercase tracking-widest mb-8 flex items-center gap-2">
              <Plus size={16} className="text-cyber-cyan" /> New_Connection
            </h3>

            <form onSubmit={handleConnect} className="space-y-6">
              <InputGroup label="Node Alias" value={formData.name} onChange={v => setFormData({...formData, name: v})} placeholder="PROD_RELAY_01" />
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-mono font-bold text-muted uppercase">Protocol</label>
                  <select 
                    value={formData.db_type}
                    onChange={e => setFormData({...formData, db_type: e.target.value})}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono focus:border-cyber-cyan/50 outline-none"
                  >
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                  </select>
                </div>
                <InputGroup label="Port" type="number" value={formData.port} onChange={v => setFormData({...formData, port: parseInt(v)})} />
              </div>

              <InputGroup label="Relay Host" value={formData.host} onChange={v => setFormData({...formData, host: v})} placeholder="10.0.0.1" />
              <InputGroup label="Database" value={formData.db_name} onChange={v => setFormData({...formData, db_name: v})} placeholder="NEURAL_CORE" />

              <div className="grid grid-cols-2 gap-4">
                <InputGroup label="Operator" value={formData.username} onChange={v => setFormData({...formData, username: v})} placeholder="admin" />
                <InputGroup label="Key" type="password" value={formData.password} onChange={v => setFormData({...formData, password: v})} placeholder="••••" />
              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded flex items-start gap-2">
                  <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
                  <p className="text-[10px] text-red-200 font-mono">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={connecting}
                className="w-full bg-cyber-cyan text-background font-mono font-bold text-xs uppercase tracking-widest py-3 rounded hover:brightness-110 transition-all disabled:opacity-20 shadow-glow-cyan/20"
              >
                {connecting ? "Initializing..." : "Stabilize Connection"}
              </button>
            </form>

            <hr className="my-6 border-white/5" />

            <h4 className="text-xs font-mono font-bold text-muted uppercase tracking-widest mb-3">Upload CSV</h4>
            <CsvUploader onComplete={() => { fetchSources(); onUpdate(); }} />
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-[10px] font-mono font-bold text-muted uppercase tracking-[0.2em]">Active_Relays</h4>
            <span className="text-[10px] font-mono text-cyber-cyan">{sources.length} NODES_ONLINE</span>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted">
              <Loader2 className="animate-spin mb-4" />
              <p className="text-[10px] font-mono uppercase tracking-widest">Scanning for data sources...</p>
            </div>
          ) : sources.length === 0 ? (
            <div className="text-center py-24 glass rounded-3xl border-dashed border-2 border-white/5">
              <Cpu size={48} className="text-white/5 mx-auto mb-4" />
              <p className="text-xs font-mono text-muted uppercase tracking-widest">{COPY.CONNECT_NO_SOURCE}</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {sources.map((source) => (
                <div key={source.id} className="glass p-6 rounded-2xl border-white/5 flex items-center gap-6 group hover:border-cyber-cyan/30 transition-all">
                  <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-cyber-cyan border border-white/10 group-hover:border-cyber-cyan/30 transition-all">
                    <Zap size={20} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h5 className="font-bold text-white uppercase tracking-tight">{source.name}</h5>
                      <div className="px-1.5 py-0.5 bg-cyber-cyan/10 border border-cyber-cyan/20 text-cyber-cyan text-[8px] font-mono font-bold rounded uppercase tracking-widest">
                        {source.db_type}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-[10px] font-mono text-muted uppercase">
                      <span className="flex items-center gap-1.5"><Globe size={10} /> {source.host}</span>
                      <span className="flex items-center gap-1.5"><Shield size={10} /> {source.db_name}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => handleDelete(source.id)}
                    className="p-3 text-white/10 hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InputGroup({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <div className="space-y-2">
      <label className="text-[10px] font-mono font-bold text-muted uppercase">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyber-cyan/50 transition-all"
      />
    </div>
  );
}

function CsvUploader({ onComplete }) {
  const [file, setFile] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [msg, setMsg] = React.useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return setMsg('Select a CSV file first');
    setLoading(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const resp = await api.uploads.uploadCsv(fd);
      if (resp.data && resp.data.success) {
        setMsg('CSV uploaded as ' + resp.data.data.table_name);
        onComplete && onComplete(resp.data.data);
      } else {
        setMsg('Upload failed');
      }
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Upload error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleUpload} className="space-y-3">
      <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0])} />
      <div className="flex items-center gap-3">
        <button className="px-3 py-2 bg-cyber-lime text-black rounded" disabled={loading}>{loading ? 'Uploading...' : 'Upload CSV'}</button>
        {msg && <div className="text-sm text-muted">{msg}</div>}
      </div>
    </form>
  );
}
