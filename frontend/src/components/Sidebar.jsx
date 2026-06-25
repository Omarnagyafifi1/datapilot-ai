import React from 'react';
import { 
  LayoutGrid, 
  Database, 
  Binary, 
  History, 
  BarChart3, 
  Settings, 
  HelpCircle,
  Cpu,
  Terminal
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { id: 'query', icon: Terminal, label: 'Query' },
  { id: 'dashboard', icon: LayoutGrid, label: 'Dashboard' },
  { id: 'datasources', icon: Database, label: 'Data Sources' },
  { id: 'schema', icon: Binary, label: 'Schema' },
  { id: 'history', icon: History, label: 'History' },
  { id: 'reports', icon: BarChart3, label: 'Reports' },
  { id: 'documentation', icon: HelpCircle, label: 'Documentation' },
  { id: 'settings', icon: Settings, label: 'Settings' },
];

export function Sidebar({ activeView, setActiveView }) {
  return (
    <aside className="w-24 border-r border-border flex flex-col items-center py-8 bg-background z-40">
      <div className="mb-12">
        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-cyber-cyan shadow-glow-cyan/20">
          <Cpu size={24} />
        </div>
      </div>

      <nav className="flex-1 flex flex-col gap-6">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveView(item.id)}
            className={cn(
              "group relative p-3 rounded-xl transition-all duration-300",
              activeView === item.id 
                ? "bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20 glow-cyan" 
                : "text-muted hover:text-white hover:bg-white/5"
            )}
            title={item.label}
          >
            <item.icon size={22} />
            {activeView === item.id && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-cyber-cyan rounded-r-full" />
            )}
            <div className="mt-2 text-[10px] text-center font-mono uppercase tracking-widest">{item.label}</div>
          </button>
        ))}
      </nav>

      <div className="flex flex-col gap-6 text-muted mt-auto">
        <button className="hover:text-white transition-colors">
          <HelpCircle size={22} />
        </button>
      </div>
    </aside>
  );
}
