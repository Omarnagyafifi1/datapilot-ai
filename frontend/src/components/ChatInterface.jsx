import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Cpu, Bot, User, Sparkles, Terminal, ChevronDown, Activity, Database, Zap } from 'lucide-react';
import { api } from '../lib/api';
import { COPY } from '../lib/copy';
import { ResultVisualizer } from './ResultVisualizer';
import { cn } from '../lib/utils';

export function ChatInterface({ selectedSourceId }) {
  const [messages, setMessages] = useState([
    { 
      id: 'welcome', 
      type: 'bot', 
      content: 'Welcome — ask a question about your data to get started.',
      timestamp: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !selectedSourceId || loading) return;

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const resp = await api.query(input, selectedSourceId);
      
      const botMessage = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: resp.data.answer,
        doc: resp.data.documentation,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: 'Query failed to execute. Please try again or check your data source.',
        isError: true,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col min-w-0">
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-12 py-10 space-y-12 no-scrollbar"
        >
          <div className="max-w-4xl mx-auto space-y-12">
            {messages.map((msg) => (
              <div key={msg.id} className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex items-center gap-3 mb-6">
                  {msg.type === 'bot' ? (
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan border border-cyber-cyan/20">
                        <Zap size={14} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-cyber-cyan tracking-widest uppercase">NEURAL_PAL_V4</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-cyber-pink/10 flex items-center justify-center text-cyber-pink border border-cyber-pink/20">
                        <User size={14} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-cyber-pink tracking-widest uppercase">OPERATOR</span>
                    </div>
                  )}
                </div>

                <div className={cn(
                  "relative p-8 rounded-2xl glass border-white/5",
                  msg.type === 'user' ? "border-l-4 border-l-cyber-pink" : "border-l-4 border-l-cyber-cyan"
                )}>
                  {msg.type === 'bot' && (
                    <div className="absolute top-4 right-6 text-[10px] font-mono text-muted flex items-center gap-2">
                      <Activity size={12} className="text-cyber-cyan animate-pulse" /> SYNC_OK
                    </div>
                  )}
                  
                  <p className={cn(
                    "text-lg leading-relaxed",
                    msg.type === 'bot' ? "text-white/90" : "text-white font-semibold"
                  )}>
                    {msg.content}
                  </p>
                  
                  {msg.doc && (
                    <div className="mt-8 border-t border-white/5 pt-8">
                      <div className="flex items-center gap-2 text-[10px] font-mono text-muted uppercase tracking-[0.2em] mb-6">
                        <ChevronDown size={14} /> Expand SQL Synthesis
                      </div>
                      <ResultVisualizer doc={msg.doc} />
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="animate-pulse">
                <div className="flex items-center gap-2 mb-6">
                  <div className="w-6 h-6 rounded bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan border border-cyber-cyan/20">
                    <Loader2 className="animate-spin" size={14} />
                  </div>
                  <span className="text-[10px] font-mono font-bold text-cyber-cyan tracking-widest uppercase">Synthesizing...</span>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-12 pt-0">
          <form 
            onSubmit={handleSend}
            className="max-w-4xl mx-auto"
          >
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-cyber-cyan via-cyber-pink to-cyber-lime rounded-2xl blur opacity-10 group-focus-within:opacity-30 transition duration-500" />
              <div className="relative bg-[#0a0a0a] border border-white/10 rounded-2xl flex items-center overflow-hidden focus-within:border-white/20 transition-all shadow-2xl">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={selectedSourceId ? "Ask a question about your data..." : COPY.PLEASE_SELECT_SOURCE}
                  disabled={!selectedSourceId || loading}
                  className="flex-1 bg-transparent px-8 py-6 text-sm text-white focus:outline-none disabled:opacity-30 font-mono"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || !selectedSourceId || loading}
                  className="mr-6 px-6 py-2 bg-cyber-lime text-background font-mono font-bold text-xs uppercase tracking-widest rounded flex items-center gap-2 hover:brightness-110 active:scale-95 transition-all disabled:opacity-20"
                >
                  {loading ? COPY.LOADING_GENERATING : COPY.PREVIEW_SQL} <Sparkles size={14} />
                </button>
              </div>
            </div>
            
            <div className="flex items-center justify-center gap-8 mt-6">
              <SuggestChip label="Predict next month's spend" onClick={() => setInput("Predict next month's spend")} />
              <SuggestChip label="Optimize SQL performance" onClick={() => setInput("Optimize SQL performance")} />
              <SuggestChip label="Export to PDF" onClick={() => {}} />
            </div>
          </form>
        </div>
      </div>

      {/* Right Intelligence Log Sidebar */}
      <aside className="w-80 border-l border-border p-8 hidden xl:block bg-background/50">
        <h5 className="text-[10px] font-mono font-bold text-cyber-pink uppercase tracking-[0.2em] mb-12">AI Intelligence<br /><span className="text-muted">Agent Transparency Log</span></h5>
        
        <div className="space-y-12">
          <LogItem label="Schema Retrieval" status="Mapped 12 relational tables and 4 JSON stores." time="0.42s" />
          <LogItem label="SQL Generation" status="Optimized for PostgreSQL 14 engine with window functions." time="0.18s" />
          <LogItem label="Optimization" status="Pruned redundant joins and verified column types." time="0.85s" />
          <LogItem label="Execution" status="Query processed across 4 data nodes." time="1.24s" />
        </div>
        
        <button className="w-full mt-12 py-3 border border-white/10 rounded-lg text-[10px] font-mono font-bold text-muted uppercase tracking-widest hover:border-white/20 hover:text-white transition-all">
          View_Full_Trace
        </button>

        <div className="mt-20 space-y-6">
          <SmallLink icon={<Zap size={14} />} label="Activity" />
          <SmallLink icon={<Terminal size={14} />} label="Logs" />
          <SmallLink icon={<Database size={14} />} label="Neural Map" />
        </div>
      </aside>
    </div>
  );
}

function SuggestChip({ label, onClick }) {
  return (
    <button 
      onClick={onClick}
      className="px-4 py-1.5 rounded-full border border-white/5 bg-white/[0.02] text-[10px] font-mono text-cyber-cyan hover:bg-cyber-cyan/10 hover:border-cyber-cyan/20 transition-all uppercase tracking-widest"
    >
      "{label}"
    </button>
  );
}

function LogItem({ label, status, time }) {
  return (
    <div className="relative pl-6 border-l border-white/10 space-y-2">
      <div className="absolute top-0 -left-1 w-2 h-2 rounded-full bg-cyber-lime" />
      <h6 className="text-[10px] font-mono font-bold text-white uppercase tracking-widest">{label}</h6>
      <p className="text-[10px] text-muted leading-relaxed">{status}</p>
      <div className="text-[9px] font-mono text-cyber-cyan">{time} • Completed</div>
    </div>
  );
}

function SmallLink({ icon, label }) {
  return (
    <div className="flex items-center gap-3 text-muted hover:text-cyber-pink cursor-pointer transition-colors group">
      <div className="group-hover:text-cyber-pink transition-colors">{icon}</div>
      <span className="text-[10px] font-mono font-bold uppercase tracking-widest">{label}</span>
    </div>
  );
}
