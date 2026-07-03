import { MessageSquare, BarChart3, Award, Settings, Cpu, Clock, Sun, Moon, Archive } from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { id: 'chat', icon: MessageSquare, label: 'Chats' },
  { id: 'history', icon: Clock, label: 'History' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics' },
  { id: 'evaluation', icon: Award, label: 'Evaluation' },
  { id: 'datasets', icon: Archive, label: 'Datasets' },
  { id: 'settings', icon: Settings, label: 'Settings' }
];

export function Sidebar({ activeView, setActiveView, themeMode, onChangeTheme }) {
  return (
    <aside className="w-24 border-r border-border flex flex-col items-center py-6 bg-background/80 backdrop-blur-md z-40">
      <div className="mb-8">
        <div className="w-10 h-10 rounded-xl bg-foreground/5 border border-border flex items-center justify-center text-cyber-cyan shadow-glow-cyan/20">
          <Cpu size={24} />
        </div>
      </div>

      <nav className="flex-1 flex flex-col gap-3.5 w-full px-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveView(item.id)}
            className={cn(
              "group relative w-full py-3.5 rounded-xl flex flex-col items-center justify-center transition-all duration-300",
              activeView === item.id 
                ? "bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20 shadow-glow-cyan/5" 
                : "text-muted hover:text-foreground hover:bg-foreground/5"
            )}
            title={item.label}
          >
            <item.icon size={20} />
            {activeView === item.id && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-cyber-cyan rounded-r-full" />
            )}
            <span className="mt-1.5 text-[9px] font-mono text-center font-bold uppercase tracking-widest leading-none scale-90 group-hover:scale-100 transition-all">
              {item.label}
            </span>
          </button>
        ))}
      </nav>

      {/* Theme Toggle Button at bottom */}
      <div className="mt-auto pt-4 border-t border-border w-full px-4 flex justify-center">
        <button
          onClick={() => onChangeTheme(themeMode === 'dark' ? 'light' : 'dark')}
          className="w-10 h-10 rounded-xl bg-foreground/5 border border-border flex items-center justify-center text-muted hover:text-foreground transition-all duration-300 active:scale-95"
          title={`Switch to ${themeMode === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {themeMode === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;