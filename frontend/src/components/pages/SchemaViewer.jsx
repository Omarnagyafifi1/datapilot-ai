import React, { useState, useEffect } from 'react';
import { Binary, ChevronRight, Table as TableIcon, Hash, Type, Key, Loader2, Database } from 'lucide-react';
import { api } from '../../lib/api';

export function SchemaViewer() {
  const [sources, setSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState(null);
  const [schema, setSchema] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTable, setActiveTable] = useState(null);

  useEffect(() => {
    const fetchSources = async () => {
      try {
        const resp = await api.datasources.list();
        if (resp.data.success) {
          setSources(resp.data.data);
          if (resp.data.data.length > 0) {
            setSelectedSourceId(resp.data.data[0].id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch sources:", err);
      }
    };
    fetchSources();
  }, []);

  useEffect(() => {
    if (!selectedSourceId) return;
    const fetchSchema = async () => {
      try {
        setLoading(true);
        const resp = await api.schema.get(selectedSourceId);
        if (resp.data.success) {
          setSchema(resp.data.data);
          if (resp.data.data.length > 0) {
            setActiveTable(resp.data.data[0]);
          } else {
            setActiveTable(null);
          }
        }
      } catch (err) {
        console.error("Failed to fetch schema:", err);
        setSchema([]);
        setActiveTable(null);
      } finally {
        setLoading(false);
      }
    };
    fetchSchema();
  }, [selectedSourceId]);

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12 flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2 text-cyber-cyan mb-4">
            <Binary size={20} />
            <span className="text-xs font-mono font-bold uppercase tracking-widest">Neural Mapping</span>
          </div>
          <h2 className="text-4xl font-extrabold tracking-tighter mb-4">SCHEMA<br /><span className="text-muted">HIERARCHY_01</span></h2>
          <p className="text-muted max-w-xl text-sm leading-relaxed">
            Distributed knowledge graph architecture. Nodes represent relational entities across your connected data streams.
          </p>
        </div>

        <div className="glass p-4 rounded-xl border-white/5 min-w-[240px]">
          <label className="text-[10px] font-mono font-bold text-muted uppercase block mb-2">Select Data Node</label>
          <select 
            value={selectedSourceId || ''}
            onChange={(e) => setSelectedSourceId(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono focus:border-cyber-cyan/50 outline-none text-white"
          >
            {sources.map(s => (
              <option key={s.id} value={s.id} className="bg-[#0a0a0a]">{s.name}</option>
            ))}
          </select>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 glass rounded-2xl border-white/5 overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-white/5 text-[10px] font-mono font-bold text-muted uppercase">Entity Tree</div>
          <div className="p-4 space-y-2 max-h-[500px] overflow-y-auto no-scrollbar">
            {loading ? (
              <div className="py-10 flex flex-col items-center justify-center text-muted">
                <Loader2 size={16} className="animate-spin mb-2" />
                <span className="text-[10px] font-mono uppercase tracking-widest">Mapping...</span>
              </div>
            ) : schema.length === 0 ? (
              <div className="text-[10px] font-mono text-muted text-center py-10 uppercase tracking-widest">Zero entities detected.</div>
            ) : (
              schema.map((table) => (
                <TreeItem 
                  key={table.name} 
                  label={table.name} 
                  active={activeTable?.name === table.name} 
                  onClick={() => setActiveTable(table)}
                />
              ))
            )}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {activeTable ? (
            <div className="glass p-6 rounded-2xl border-cyber-cyan/20 glow-cyan animate-in fade-in zoom-in-95 duration-300">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h4 className="text-xl font-bold font-mono text-cyber-cyan">{activeTable.name}</h4>
                  <p className="text-xs text-muted">Schema mapping for {activeTable.name} entity.</p>
                </div>
                <TableIcon className="text-white/20" size={32} />
              </div>

              <div className="space-y-3">
                {activeTable.columns.map((col) => (
                  <ColumnItem key={col.name} name={col.name} type={col.type} pkey={col.primary_key} />
                ))}
              </div>
            </div>
          ) : (
            <div className="glass p-12 rounded-2xl border-white/5 text-center flex flex-col items-center justify-center text-muted">
              <Database size={48} className="opacity-10 mb-4" />
              <p className="text-xs font-mono uppercase tracking-widest">No table selected or detected.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TreeItem({ label, active, onClick }) {
  return (
    <div 
      onClick={onClick}
      className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${active ? 'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20' : 'text-white/50 hover:bg-white/5'}`}
    >
      <ChevronRight size={14} className={active ? '' : 'text-white/20'} />
      <span className="text-xs font-mono truncate">{label}</span>
    </div>
  );
}

function ColumnItem({ name, type, pkey }) {
  return (
    <div className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/5 rounded-xl">
      <div className="flex items-center gap-3">
        {pkey ? <Key size={14} className="text-cyber-lime" /> : <Hash size={14} className="text-white/20" />}
        <span className="text-xs font-mono text-white/90">{name}</span>
      </div>
      <span className="text-[10px] font-mono text-muted border border-white/10 px-1.5 py-0.5 rounded">{type}</span>
    </div>
  );
}
