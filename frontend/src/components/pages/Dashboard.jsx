import React, { useState, useEffect } from 'react';
import { Sparkles, Terminal, ArrowRight, Zap, Database, Share2, Loader2 } from 'lucide-react';
import heroPurple from '../../assets/illustrations/isometric-neon-purple.svg';

import { api } from '../../lib/api';

export function Dashboard({ onStartAnalyst, onManageSources, onViewHistory }) {
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFeed = async () => {
      try {
        setLoading(true);
        const resp = await api.system.feed();
        if (resp.data.success) {
          setFeed(resp.data.data);
        }
      } catch (err) {
        console.error("Failed to fetch feed:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchFeed();
  }, []);

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
        <span className="text-xs font-mono text-muted uppercase tracking-[0.2em]">System Online</span>
      </div>

      <h1 className="text-6xl font-extrabold mb-8 tracking-tighter leading-tight">
        Synthesize your <span className="text-cyber-cyan italic">Data Stream.</span>
      </h1>

      <p className="text-xl text-muted max-w-2xl mb-6 leading-relaxed">
        Interact with the core neural engine. Ask complex queries across your heterogeneous data sources in natural language.
      </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16 items-center">
            <div>
              {/* left column stays as the feature cards */}
            </div>
            <div className="flex items-center justify-center">
              {/* Illustration: replace placeholder SVGs in assets/illustrations with licensed ones */}
              <img src={heroPurple} alt="Isometric illustration" className="w-96 h-72" loading="lazy" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <div className="glass p-8 rounded-2xl group hover:border-cyber-cyan/30 transition-all cursor-pointer relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Sparkles size={120} />
          </div>
          <div className="w-12 h-12 rounded-xl bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan mb-6">
            <Zap size={24} />
          </div>
          <h3 className="text-xl font-bold mb-3">Neural Synthesis</h3>
          <p className="text-muted text-sm leading-relaxed mb-6">Execute multi-hop reasoning across your schema to find deep correlations and anomalies.</p>
          <button 
            onClick={onStartAnalyst}
            className="flex items-center gap-2 text-cyber-cyan font-mono text-xs font-bold uppercase tracking-widest hover:gap-4 transition-all"
          >
            Initialize Engine <ArrowRight size={14} />
          </button>
        </div>

        <div className="glass p-8 rounded-2xl group hover:border-cyber-lime/30 transition-all cursor-pointer relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Database size={120} />
          </div>
          <div className="w-12 h-12 rounded-xl bg-cyber-lime/10 flex items-center justify-center text-cyber-lime mb-6">
            <Database size={24} />
          </div>
          <h3 className="text-xl font-bold mb-3">Data Orchestrator</h3>
          <p className="text-muted text-sm leading-relaxed mb-6">Map and connect your distributed databases into a single unified knowledge graph.</p>
          <button onClick={onManageSources} className="flex items-center gap-2 text-cyber-lime font-mono text-xs font-bold uppercase tracking-widest hover:gap-4 transition-all">
            Manage Sources <ArrowRight size={14} />
          </button>
        </div>
      </div>

      <div className="border-t border-white/5 pt-12">
        <div className="flex items-center justify-between mb-8">
          <h4 className="text-xs font-mono font-bold text-muted uppercase tracking-widest flex items-center gap-2">
            <Terminal size={14} /> Active Feed
          </h4>
          <span onClick={onViewHistory} className="text-[10px] font-mono text-cyber-cyan underline cursor-pointer">View full logs</span>
        </div>

        <div className="space-y-4">
          {loading ? (
            <div className="py-10 flex flex-col items-center justify-center text-muted">
              <Loader2 size={16} className="animate-spin mb-2" />
              <span className="text-[10px] font-mono uppercase tracking-widest">Scanning network feed...</span>
            </div>
          ) : feed.length === 0 ? (
            <div className="text-[10px] font-mono text-muted text-center py-10 uppercase tracking-widest">No recent activity detected.</div>
          ) : (
            feed.map((item) => (
              <FeedItem 
                key={item.id}
                type={item.type} 
                content={item.content} 
                time={new Date(item.timestamp).toLocaleTimeString()} 
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function FeedItem({ type, content, time }) {
  return (
    <div className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.04] transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-1.5 h-1.5 rounded-full bg-cyber-cyan" />
        <div>
          <p className="text-[10px] font-mono font-bold text-muted uppercase mb-0.5">{type}</p>
          <p className="text-xs text-white/70">{content}</p>
        </div>
      </div>
      <span className="text-[10px] font-mono text-muted">{time}</span>
    </div>
  );
}
