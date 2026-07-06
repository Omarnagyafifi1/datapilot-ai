import { useState, useRef, useEffect } from 'react';
import { 
  Send, Loader2, User, ChevronDown, 
  Activity, Zap, Plus, Trash2, Edit2, Check, Search, 
  Copy, RotateCcw, StopCircle, PanelRightOpen, PanelRightClose, BookOpen
} from 'lucide-react';
import { api } from '../lib/api';
import { COPY } from '../lib/copy';
import { ResultVisualizer } from './ResultVisualizer';
import { cn } from '../lib/utils';

// Helper to format timestamps
function formatTime(isoString) {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return 'Now';
  }
}

// Simple Markdown Renderer
function renderMarkdown(text) {
  if (!text) return '';
  
  // Format code blocks
  let formatted = text.replace(/```([\s\S]*?)```/g, (match, code) => {
    // Trim leading language name if any
    const codeLines = code.trim().split('\n');
    let lang = 'sql';
    let cleanCode = code.trim();
    if (codeLines[0] && codeLines[0].length < 15 && !codeLines[0].includes(' ') && !codeLines[0].includes('(')) {
      lang = codeLines[0].toLowerCase();
      cleanCode = codeLines.slice(1).join('\n');
    }
    return `<div class="bg-foreground/5 border border-border rounded-xl my-4 overflow-hidden font-mono text-xs">
      <div class="bg-foreground/5 px-4 py-1.5 flex items-center justify-between text-[10px] text-muted uppercase font-bold tracking-widest border-b border-border">
        <span>${lang}</span>
      </div>
      <pre class="p-4 overflow-x-auto text-cyber-cyan leading-relaxed">${cleanCode}</pre>
    </div>`;
  });

  // Format bold text
  formatted = formatted.replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>');

  // Format inline code
  formatted = formatted.replace(/`([^`\n]+)`/g, '<code class="text-cyber-cyan bg-white/5 px-1.5 py-0.5 rounded font-mono text-xs font-semibold">$1</code>');

  // Format list items
  formatted = formatted.replace(/^\s*-\s+(.+)$/gm, '<li class="ml-4 list-disc text-foreground/80 my-1">$1</li>');

  return <div className="space-y-2 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatted }} />;
}

export default function ChatInterface({ 
  selectedSourceId: initialSelectedSourceId, 
  dataSources = [], 
  onUpdateSources,
  onSelectSource
}) {
  // Conversational history system
  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem('dp_conversations');
    if (saved) {
      try { return JSON.parse(saved); } catch { return []; }
    }
    return [];
  });

  const [activeChatId, setActiveChatId] = useState(() => {
    const saved = localStorage.getItem('dp_active_chat_id');
    return saved || null;
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [editingTitleId, setEditingTitleId] = useState(null);
  const [editTitleText, setEditTitleText] = useState('');

  // active messages state
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
  const [abortController, setAbortController] = useState(null);
  const [copiedMessageId, setCopiedMessageId] = useState(null);

  // Right Panel state
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [rightPanelTab, setRightPanelTab] = useState('schema'); // 'schema' | 'sources'

  // Schema state
  const [schemaList, setSchemaList] = useState([]);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [activeSchemaTable, setActiveSchemaTable] = useState(null);

  // CSV/Database connect state inside right panel
  const [connectError, setConnectError] = useState(null);
  const [connectLoading, setConnectLoading] = useState(false);
  const [dbFormData, setDbFormData] = useState({
    name: '', db_type: 'sqlite', host: '', port: 5432, db_name: '', username: '', password: ''
  });

  // Dynamic suggestion chips
  const [suggestionChips, setSuggestionChips] = useState([]);

  // LLM settings state - loaded from backend
  const [llmSettings, setLlmSettings] = useState({
    provider: 'groq',
    model: 'llama-3.3-70b-versatile',
    temperature: 0.2,
    maxTokens: 2048
  });

  const scrollRef = useRef(null);

  // Load LLM settings from backend on mount
  useEffect(() => {
    api.settings.get()
      .then(resp => {
        if (resp.data?.success && resp.data?.data) {
          const settings = resp.data.data;
          setLlmSettings({
            provider: settings.llm_provider || settings.provider || 'groq',
            model: settings.model || 'llama-3.3-70b-versatile',
            temperature: settings.temperature ?? 0.2,
            maxTokens: settings.max_tokens ?? 2048
          });
        }
      })
      .catch(err => {
        console.warn('Could not load LLM settings from backend:', err);
      });
  }, []);

  // Load current messages when activeChatId changes
  useEffect(() => {
    if (activeChatId) {
      const activeChat = conversations.find(c => c.id === activeChatId);
      if (activeChat) {
        setMessages(activeChat.messages || []);
      }
    } else {
      setMessages([
        { 
          id: 'welcome', 
          type: 'bot', 
          content: 'Welcome operators — ask a question about your database to get started. Choose your connected database relay above to configure context.',
          timestamp: new Date().toISOString()
        }
      ]);
    }
  }, [activeChatId]);

  // Save conversations to localStorage
  useEffect(() => {
    localStorage.setItem('dp_conversations', JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem('dp_active_chat_id', activeChatId);
    } else {
      localStorage.removeItem('dp_active_chat_id');
    }
  }, [activeChatId]);

  // Fetch schema when DB source changes
  useEffect(() => {
    if (!initialSelectedSourceId) {
      setSchemaList([]);
      setActiveSchemaTable(null);
      return;
    }
    const fetchSchema = async () => {
      try {
        setSchemaLoading(true);
        const resp = await api.schema.get(initialSelectedSourceId);
        if (resp.data.success) {
          setSchemaList(resp.data.data);
          if (resp.data.data.length > 0) {
            setActiveSchemaTable(resp.data.data[0]);
          } else {
            setActiveSchemaTable(null);
          }
        }
      } catch (err) {
        console.error("Failed to fetch schema", err);
        setSchemaList([]);
      } finally {
        setSchemaLoading(false);
      }
    };
    fetchSchema();
  }, [initialSelectedSourceId]);

  // Fetch dynamic suggestion chips when source changes
  useEffect(() => {
    if (!initialSelectedSourceId) {
      setSuggestionChips([]);
      return;
    }
    api.schema.suggestions(initialSelectedSourceId)
      .then(resp => {
        if (resp.data?.success && resp.data?.data?.length > 0) {
          setSuggestionChips(resp.data.data.slice(0, 3));
        } else {
          setSuggestionChips([]);
        }
      })
      .catch(() => setSuggestionChips([]));
  }, [initialSelectedSourceId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, loadingStage]);




  // Create new conversation session
  const startNewChat = () => {
    const newId = Date.now().toString();
    const newChat = {
      id: newId,
      title: 'New conversation ' + new Date().toLocaleDateString(),
      messages: [],
      selectedSourceId: initialSelectedSourceId,
      provider: llmSettings.provider,
      model: llmSettings.model,
      timestamp: new Date().toISOString()
    };
    setConversations(prev => [newChat, ...prev]);
    setActiveChatId(newId);
  };

  // Delete conversation
  const deleteConversation = (id, e) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat history?")) return;
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeChatId === id) {
      setActiveChatId(null);
    }
  };

  // Rename conversation
  const startRename = (id, title, e) => {
    e.stopPropagation();
    setEditingTitleId(id);
    setEditTitleText(title);
  };

  const saveRename = (id) => {
    if (editTitleText.trim()) {
      setConversations(prev => prev.map(c => c.id === id ? { ...c, title: editTitleText } : c));
    }
    setEditingTitleId(null);
  };

  // Send Message Flow
  const handleSend = async (e, textOverride = null) => {
    if (e) e.preventDefault();
    const queryText = textOverride || input;
    if (!queryText.trim() || !initialSelectedSourceId || loading) return;

    const userMsgId = Date.now().toString();
    const userMessage = {
      id: userMsgId,
      type: 'user',
      content: queryText,
      timestamp: new Date().toISOString()
    };

    let chatSessionId = activeChatId;
    let isNew = false;
    if (!chatSessionId) {
      chatSessionId = Date.now().toString();
      isNew = true;
    }

    // Add user message to current list
    setMessages(prev => [...prev.filter(m => m.id !== 'welcome'), userMessage]);
    if (!textOverride) setInput('');
    setLoading(true);
    setLoadingStage('Analyzing query syntax...');

    const controller = new AbortController();
    setAbortController(controller);
    const loadingTimers = [];
    const clearLoadingTimers = () => {
      loadingTimers.forEach(clearTimeout);
      loadingTimers.length = 0;
    };

    try {
      // Step simulated updates
      loadingTimers.push(setTimeout(() => setLoadingStage('Interpreting database schema map...'), 1000));
      loadingTimers.push(setTimeout(() => setLoadingStage('Generating optimized SQL plan...'), 2200));
      loadingTimers.push(setTimeout(() => setLoadingStage('Executing query & building analytics...'), 3500));

      const resp = await api.query(queryText, initialSelectedSourceId, chatSessionId, false, null, {
        signal: controller.signal,
      }, llmSettings);

      const payload = resp.data?.data ?? resp.data ?? {};
      const derivedDoc = {
        ...(payload.documentation || {}),
        sql: payload.sql || null,
        results: payload.results || [],
        results_count: payload.results_count ?? (payload.results || []).length,
        visualization: payload.visualization || payload.documentation?.visualization || null,
        insights: payload.insights || [],
        suggestions: payload.suggestions || [],
        thread_id: payload.thread_id || chatSessionId,
        source_id: initialSelectedSourceId,
        question: queryText,
        executed_at: payload.executed_at || new Date().toISOString(),
        status: payload.status || 'completed',
      };

      clearLoadingTimers();

      const botMessage = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: payload.answer || payload.message || (payload.requires_approval ? 'This query will modify data. Approve or deny below.' : 'Completed execution of generated query.'),
        doc: derivedDoc,
        requiresApproval: !!payload.requires_approval,
        approvalRequest: payload.approval_request || null,
        approvalThreadId: payload.requires_approval ? (payload.thread_id || chatSessionId) : null,
        timestamp: new Date().toISOString()
      };

      const updatedMsgs = [...messages.filter(m => m.id !== 'welcome'), userMessage, botMessage];
      setMessages(updatedMsgs);

      // Save/Update conversation
      if (isNew) {
        const newChat = {
          id: chatSessionId,
          title: queryText.slice(0, 30) + (queryText.length > 30 ? '...' : ''),
          messages: updatedMsgs,
          selectedSourceId: initialSelectedSourceId,
          provider: llmSettings.provider,
          model: llmSettings.model,
          timestamp: new Date().toISOString()
        };
        setConversations(prev => [newChat, ...prev]);
        setActiveChatId(chatSessionId);
      } else {
        setConversations(prev => prev.map(c => c.id === chatSessionId ? { ...c, messages: updatedMsgs, timestamp: new Date().toISOString() } : c));
      }

    } catch (err) {
      clearLoadingTimers();
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
      const errMsg = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: 'Query failed to compile or execute. Check schema or connected data connection.',
        isError: true,
        timestamp: new Date().toISOString()
      };
      const updatedMsgs = [...messages.filter(m => m.id !== 'welcome'), userMessage, errMsg];
      setMessages(updatedMsgs);
      if (!isNew) {
        setConversations(prev => prev.map(c => c.id === chatSessionId ? { ...c, messages: updatedMsgs } : c));
      }
    } finally {
      clearLoadingTimers();
      setLoading(false);
      setLoadingStage('');
      setAbortController(null);
    }
  };

  const handleApprove = async (msgId, threadId) => {
    try {
      const resp = await api.queryApproval(threadId, true);
      const payload = resp.data?.data ?? resp.data ?? {};
      const updatedDoc = {
        ...payload.documentation,
        sql: payload.sql || null,
        results: payload.results || [],
        results_count: payload.results_count ?? (payload.results || []).length,
        visualization: payload.visualization || payload.documentation?.visualization || null,
        insights: payload.insights || [],
        suggestions: payload.suggestions || [],
        question: payload.question || '',
        executed_at: payload.executed_at || new Date().toISOString(),
        status: payload.status || 'completed',
      };
      setMessages(prev => prev.map(m => m.id === msgId ? {
        ...m,
        content: payload.answer || payload.message || 'Query approved and executed.',
        doc: updatedDoc,
        requiresApproval: false,
        approvalRequest: null,
        approvalThreadId: null,
      } : m));
    } catch (err) {
      setMessages(prev => prev.map(m => m.id === msgId ? {
        ...m,
        content: 'Approval failed: ' + (err.message || 'Unknown error'),
        requiresApproval: false,
        approvalRequest: null,
        approvalThreadId: null,
      } : m));
    }
  };

  const handleDeny = async (msgId, threadId) => {
    try {
      await api.queryApproval(threadId, false);
      setMessages(prev => prev.map(m => m.id === msgId ? {
        ...m,
        content: 'Operation cancelled by user.',
        requiresApproval: false,
        approvalRequest: null,
        approvalThreadId: null,
        doc: { ...m.doc, insights: [], suggestions: [] },
      } : m));
    } catch (err) {
      setMessages(prev => prev.map(m => m.id === msgId ? {
        ...m,
        content: 'Failed to cancel: ' + (err.message || 'Unknown error'),
      } : m));
    }
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setLoading(false);
      setLoadingStage('');
      setAbortController(null);
    }
  };

  const handleRegenerate = () => {
    const userMsgs = messages.filter(m => m.type === 'user');
    if (userMsgs.length > 0) {
      const lastQuestion = userMsgs[userMsgs.length - 1].content;
      handleSend(null, lastQuestion);
    }
  };

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedMessageId(id);
    setTimeout(() => setCopiedMessageId(null), 1500);
  };

  // Connect database inside right panel
  const handleConnectDb = async (e) => {
    e.preventDefault();
    setConnectLoading(true);
    setConnectError(null);
    try {
      const resp = await api.datasources.connect(dbFormData);
      if (resp.data.success) {
        onUpdateSources();
        setDbFormData({ name: '', db_type: 'sqlite', host: '', port: 5432, db_name: '', username: '', password: '' });
        setRightPanelTab('schema');
      }
    } catch (err) {
      setConnectError(err.response?.data?.detail || "Connection failed.");
    } finally {
      setConnectLoading(false);
    }
  };

  const handleDeleteDb = async (id, e) => {
    e.stopPropagation();
    if (!confirm("Decommission this connection node?")) return;
    try {
      await api.datasources.delete(id);
      onUpdateSources();
    } catch (err) {
      console.error(err);
    }
  };

  // Filter conversations based on query
  const filteredChats = conversations.filter(c => 
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.messages.some(m => m.content.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden relative">
      {/* 1. Left Side conversation panel */}
      <aside className="w-80 border-r border-border flex flex-col bg-background/95 shrink-0 z-10">
        <div className="p-4 border-b border-border space-y-3">
          <button 
            onClick={startNewChat}
            className="w-full py-3 bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/30 text-cyber-cyan font-mono font-bold text-xs uppercase tracking-widest rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <Plus size={16} /> New Session
          </button>

          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted group-focus-within:text-cyber-cyan transition-colors" size={14} />
            <input
              placeholder="Search chat history..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-foreground/5 border border-border rounded-lg py-2 pl-9 pr-4 text-xs text-foreground focus:outline-none focus:border-cyber-cyan/40 transition-all font-mono"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto no-scrollbar py-3 px-2 space-y-1.5">
          {filteredChats.length === 0 ? (
            <div className="text-[10px] font-mono text-muted text-center py-10 uppercase tracking-widest">
              Zero records.
            </div>
          ) : (
            filteredChats.map((chat) => {
              const isActive = chat.id === activeChatId;
              const isEditing = chat.id === editingTitleId;
              return (
                <div 
                  key={chat.id}
                  onClick={() => setActiveChatId(chat.id)}
                  className={cn(
                    "group relative p-3.5 rounded-xl cursor-pointer transition-all border border-transparent",
                    isActive 
                      ? "bg-foreground/5 border-border text-foreground" 
                      : "text-muted hover:text-foreground/80 hover:bg-foreground/[0.02]"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {isEditing ? (
                        <input
                          value={editTitleText}
                          onChange={(e) => setEditTitleText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveRename(chat.id);
                            if (e.key === 'Escape') setEditingTitleId(null);
                          }}
                          autoFocus
                          className="bg-background border border-cyber-cyan/30 text-foreground text-xs px-2 py-1 rounded w-full outline-none font-mono"
                        />
                      ) : (
                        <>
                          <p className="text-xs font-semibold truncate leading-normal">{chat.title}</p>
                          <span className="text-[9px] font-mono text-muted mt-1 block">
                            {formatTime(chat.timestamp)}
                          </span>
                        </>
                      )}
                    </div>

                    {!isEditing && (
                      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
                        <button 
                          onClick={(e) => startRename(chat.id, chat.title, e)}
                          className="p-1 hover:text-cyber-cyan rounded"
                          title="Rename"
                        >
                          <Edit2 size={11} />
                        </button>
                        <button 
                          onClick={(e) => deleteConversation(chat.id, e)}
                          className="p-1 hover:text-red-400 rounded"
                          title="Delete"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    )}

                    {isEditing && (
                      <button 
                        onClick={() => saveRename(chat.id)}
                        className="p-1 text-cyber-lime rounded"
                      >
                        <Check size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* 2. Center Chat Stream area */}
      <main className="flex-1 flex flex-col min-w-0 bg-background/30 relative">
        {/* Toggle Right Panel Button */}
        <button
          onClick={() => setShowRightPanel(!showRightPanel)}
          className="absolute top-4 right-4 z-20 p-2.5 bg-background border border-border text-muted hover:text-foreground rounded-xl transition-all active:scale-95"
          title="Toggle database helper sidebar"
        >
          {showRightPanel ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
        </button>

        {/* Top bar with active configurations */}
        <div className="h-14 border-b border-border flex items-center justify-between px-8 bg-background/40">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-cyber-cyan animate-pulse" />
            <span className="text-[10px] font-mono font-bold tracking-widest text-foreground/50 uppercase">
              ACTIVE_STREAM
            </span>
          </div>


        </div>

        {/* Chat message containers */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-8 py-6 space-y-8 no-scrollbar"
        >
          <div className="max-w-4xl mx-auto space-y-8">
            {messages.map((msg) => {
              const isBot = msg.type === 'bot';
              return (
                <div key={msg.id} className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {isBot ? (
                        <>
                          <div className="w-5 h-5 rounded bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan border border-cyber-cyan/20">
                            <Zap size={11} />
                          </div>
                          <span className="text-[9px] font-mono font-bold text-cyber-cyan tracking-widest uppercase">DATAPILOT_AI</span>
                        </>
                      ) : (
                        <>
                          <div className="w-5 h-5 rounded bg-cyber-pink/10 flex items-center justify-center text-cyber-pink border border-cyber-pink/20">
                            <User size={11} />
                          </div>
                          <span className="text-[9px] font-mono font-bold text-cyber-pink tracking-widest uppercase">OPERATOR</span>
                        </>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono text-muted">{formatTime(msg.timestamp)}</span>
                      <button 
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="p-1 hover:text-foreground text-muted transition-colors"
                        title="Copy text"
                      >
                        {copiedMessageId === msg.id ? <Check size={11} className="text-cyber-lime" /> : <Copy size={11} />}
                      </button>
                    </div>
                  </div>

                  <div className={cn(
                    "relative p-6 rounded-2xl border border-border",
                    isBot ? "bg-card border-l-2 border-l-cyber-cyan" : "bg-foreground/[0.02] border-l-2 border-l-cyber-pink"
                  )}>
                    {renderMarkdown(msg.content)}

                    {/* Approval UI for write queries */}
                    {isBot && msg.requiresApproval && msg.approvalRequest && (
                      <div className="mt-6 space-y-4">
                        <div className="glass p-4 rounded-xl border border-amber-500/30 bg-amber-500/5">
                          <div className="flex items-center gap-2 text-[11px] font-bold text-amber-400 uppercase tracking-widest mb-2">
                            <Zap size={14} /> Pending Approval
                          </div>
                          <div className="font-mono text-xs text-foreground/80 bg-black/30 p-3 rounded-lg mb-4 overflow-x-auto whitespace-pre">
                            {msg.approvalRequest.sql || msg.doc?.sql || 'No SQL available'}
                          </div>
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleApprove(msg.id, msg.approvalThreadId)}
                              className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold font-mono bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 rounded-lg hover:bg-emerald-500/30 transition-colors"
                            >
                              <Check size={14} /> Approve & Execute
                            </button>
                            <button
                              onClick={() => handleDeny(msg.id, msg.approvalThreadId)}
                              className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold font-mono bg-red-500/20 border border-red-500/50 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors"
                            >
                              <Trash2 size={14} /> Deny
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Integrated Query Results - Expandable block */}
                    {isBot && msg.doc && !msg.requiresApproval && (
                      <div className="mt-8 border-t border-white/5 pt-8">
                        <div className="flex items-center gap-2 text-[10px] font-mono text-muted uppercase tracking-[0.2em] mb-6">
                          <ChevronDown size={14} /> Expand SQL Synthesis
                        </div>
                        <ResultVisualizer doc={msg.doc} />
                      </div>
                    )}

                    {msg.eval && (
                      <div className="mt-8 border-t border-white/5 pt-8">
                        <div className="flex items-center gap-2 text-[10px] font-mono text-cyber-cyan uppercase tracking-[0.2em] mb-4">
                          <Activity size={14} /> AI Quality Evaluation
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-black/30 p-4 rounded-lg border border-cyber-cyan/10">
                            <div className="text-[10px] font-mono text-muted uppercase tracking-widest mb-1">Overall</div>
                            <div className="text-2xl font-mono font-bold text-cyber-cyan">{(msg.eval.overall * 100).toFixed(0)}%</div>
                          </div>
                          <div className="bg-black/30 p-4 rounded-lg border border-white/5">
                            <div className="text-[10px] font-mono text-muted uppercase tracking-widest mb-1">Correctness</div>
                            <div className="text-xl font-mono text-white">{(msg.eval.correctness * 100).toFixed(0)}%</div>
                          </div>
                          <div className="bg-black/30 p-4 rounded-lg border border-white/5">
                            <div className="text-[10px] font-mono text-muted uppercase tracking-widest mb-1">Schema</div>
                            <div className="text-xl font-mono text-white">{(msg.eval.schema_score * 100).toFixed(0)}%</div>
                          </div>
                          <div className="bg-black/30 p-4 rounded-lg border border-white/5">
                            <div className="text-[10px] font-mono text-muted uppercase tracking-widest mb-1">Efficiency</div>
                            <div className="text-xl font-mono text-white">{(msg.eval.efficiency * 100).toFixed(0)}%</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            
            {loading && (
              <div className="animate-in fade-in duration-300">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-5 h-5 rounded bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan border border-cyber-cyan/20">
                    <Loader2 className="animate-spin text-cyber-cyan" size={11} />
                  </div>
                  <span className="text-[9px] font-mono font-bold text-cyber-cyan tracking-widest uppercase animate-pulse">
                    {loadingStage}
                  </span>
                </div>
                <div className="bg-card border border-border border-l-2 border-l-cyber-cyan/50 p-6 rounded-2xl w-full">
                  <div className="flex flex-col gap-2">
                    <div className="h-3.5 bg-foreground/5 rounded-full w-3/4 animate-pulse" />
                    <div className="h-3.5 bg-foreground/5 rounded-full w-5/6 animate-pulse" />
                    <div className="h-3.5 bg-foreground/5 rounded-full w-1/2 animate-pulse" />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Message Composer Footer */}
        <div className="p-8 pt-0 bg-gradient-to-t from-background via-background to-transparent z-10">
          <form 
            onSubmit={handleSend}
            className="max-w-4xl mx-auto"
          >
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-cyber-cyan via-cyber-pink to-cyber-lime rounded-2xl blur opacity-5 group-focus-within:opacity-15 transition duration-500" />
              <div className="relative bg-card border border-border rounded-2xl flex flex-col focus-within:border-cyber-cyan/30 transition-all shadow-2xl">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  rows={2}
                  placeholder={initialSelectedSourceId ? "Submit prompt to query schema, run SQL execution, or generate analytical reports..." : COPY.PLEASE_SELECT_SOURCE}
                  disabled={!initialSelectedSourceId || loading}
                  className="w-full bg-transparent px-6 py-4 text-sm text-foreground focus:outline-none disabled:opacity-30 font-mono resize-none"
                />

                <div className="px-4 py-2 border-t border-border flex items-center justify-between bg-foreground/5">
                  <div className="flex items-center gap-4">
                    {loading ? (
                      <button
                        type="button"
                        onClick={handleStop}
                        className="px-3.5 py-1.5 border border-red-500/30 text-red-400 bg-red-500/5 font-mono text-[10px] uppercase tracking-widest rounded flex items-center gap-1.5 hover:bg-red-500/10 transition-all"
                      >
                        <StopCircle size={12} /> Stop
                      </button>
                    ) : (
                      messages.length > 1 && (
                        <button
                          type="button"
                          onClick={handleRegenerate}
                          className="px-3.5 py-1.5 border border-border text-muted hover:text-foreground font-mono text-[10px] uppercase tracking-widest rounded flex items-center gap-1.5 hover:bg-foreground/5 transition-all"
                        >
                          <RotateCcw size={12} /> Regenerate
                        </button>
                      )
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={!input.trim() || !initialSelectedSourceId || loading}
                    className="px-5 py-2 bg-cyber-lime text-black font-mono font-bold text-xs uppercase tracking-widest rounded-lg flex items-center gap-2 hover:brightness-110 active:scale-95 transition-all disabled:opacity-20 shadow-glow-lime/20"
                  >
                    <span>Execute Flow</span>
                    <Send size={12} />
                  </button>
                </div>
              </div>
            </div>
            
            {/* Quick Suggestions Chips */}
            <div className="flex items-center justify-center gap-4 mt-4 overflow-x-auto no-scrollbar py-1">
              {(suggestionChips.length > 0 ? suggestionChips : []).map((chip, i) => {
                const label = chip.en || chip.ar || chip;
                return (
                  <SuggestChip key={i} label={label} onClick={() => setInput(label)} />
                );
              })}
            </div>
          </form>
        </div>
      </main>

      {/* 3. Collapsible Right side utility panel */}
      {showRightPanel && (
        <aside className="w-80 border-l border-border flex flex-col bg-background/95 shrink-0 z-10 animate-in slide-in-from-right duration-300">
          <div className="flex border-b border-border bg-foreground/[0.01]">
            <button
              onClick={() => setRightPanelTab('schema')}
              className={cn(
                "flex-1 py-3 text-[10px] font-mono font-bold uppercase tracking-wider text-center border-b-2 transition-all",
                rightPanelTab === 'schema' ? "border-cyber-cyan text-cyber-cyan bg-cyber-cyan/5" : "border-transparent text-muted hover:text-foreground"
              )}
            >
              Schema Viewer
            </button>
            <button
              onClick={() => setRightPanelTab('sources')}
              className={cn(
                "flex-1 py-3 text-[10px] font-mono font-bold uppercase tracking-wider text-center border-b-2 transition-all",
                rightPanelTab === 'sources' ? "border-cyber-cyan text-cyber-cyan bg-cyber-cyan/5" : "border-transparent text-muted hover:text-foreground"
              )}
            >
              Data Nodes
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
            {/* Schema Tab */}
            {rightPanelTab === 'schema' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-muted uppercase">ACTIVE SCHEMA</span>
                  <span className="text-[10px] font-mono text-cyber-cyan">{schemaList.length} entities</span>
                </div>

                {schemaLoading ? (
                  <div className="py-20 flex flex-col items-center justify-center text-muted">
                    <Loader2 size={16} className="animate-spin mb-2" />
                    <span className="text-[9px] font-mono uppercase tracking-widest">Mapping tree...</span>
                  </div>
                ) : schemaList.length === 0 ? (
                  <div className="text-center py-10 text-[10px] font-mono text-muted uppercase">
                    Zero tables online.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {/* Entity drop lists */}
                    {schemaList.map((table) => {
                      const isOpen = activeSchemaTable?.name === table.name;
                      return (
                        <div key={table.name} className="border border-border rounded-xl bg-foreground/[0.01] overflow-hidden">
                          <button
                            onClick={() => setActiveSchemaTable(isOpen ? null : table)}
                            className="w-full flex items-center justify-between p-3 text-left hover:bg-foreground/[0.02] transition-colors"
                          >
                            <span className="text-xs font-mono font-bold text-foreground/95 truncate">{table.name}</span>
                            <ChevronDown size={14} className={cn("text-muted transition-transform", isOpen && "transform rotate-180")} />
                          </button>
                          
                          {isOpen && (
                            <div className="px-3 pb-3 border-t border-border divide-y divide-border space-y-1.5 pt-1.5">
                              {table.columns.map((col) => (
                                <div key={col.name} className="flex items-center justify-between text-[10px] font-mono py-1.5">
                                  <span className="text-foreground/80">{col.name}</span>
                                  <span className="text-muted text-[9px] uppercase">{col.type}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Sources Connection Tab */}
            {rightPanelTab === 'sources' && (
              <div className="space-y-6">
                {/* Active Data Nodes */}
                <div className="space-y-3">
                  <div className="text-[10px] font-mono text-muted uppercase">ACTIVE RELAYS</div>
                  
                  {dataSources.length === 0 ? (
                    <div className="text-center py-6 text-[10px] font-mono text-muted uppercase">No data connections.</div>
                  ) : (
                    <div className="space-y-2">
                      {dataSources.map((source) => {
                        const isSel = source.id === initialSelectedSourceId;
                        return (
                          <div 
                            key={source.id}
                            onClick={() => onSelectSource(source.id)}
                            className={cn(
                              "p-3 rounded-xl border border-border bg-foreground/[0.01] hover:border-cyber-cyan/30 transition-all flex items-center justify-between cursor-pointer",
                              isSel && "border-cyber-cyan/50 bg-cyber-cyan/[0.02]"
                            )}
                          >
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-foreground truncate flex items-center gap-1.5">
                                {source.name}
                                {isSel && <span className="w-1.5 h-1.5 rounded-full bg-cyber-lime animate-pulse" />}
                              </p>
                              <span className="text-[9px] font-mono text-muted capitalize mt-0.5 block">{source.db_type} relay</span>
                            </div>
                            <button
                              onClick={(e) => handleDeleteDb(source.id, e)}
                              className="p-1.5 text-muted hover:text-red-400 hover:bg-foreground/5 rounded"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Add Data Relay Form */}
                <div className="border-t border-border pt-4 space-y-4">
                  <span className="text-[10px] font-mono text-muted uppercase">CONNECT NEW RELAY</span>
                  
                  <form onSubmit={handleConnectDb} className="space-y-3">
                    <input
                      type="text"
                      placeholder="Relay Alias (e.g. STAGING_DB)"
                      value={dbFormData.name}
                      onChange={e => setDbFormData({...dbFormData, name: e.target.value})}
                      required
                      className="w-full bg-foreground/5 border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                    />

                    <select
                      value={dbFormData.db_type}
                      onChange={e => setDbFormData({...dbFormData, db_type: e.target.value})}
                      className="w-full bg-card border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                    >
                      <option value="sqlite" className="bg-card text-foreground">SQLite File</option>
                      <option value="postgresql" className="bg-card text-foreground">PostgreSQL</option>
                      <option value="mysql" className="bg-card text-foreground">MySQL</option>
                      <option value="mssql" className="bg-card text-foreground">SQL Server</option>
                    </select>

                    {dbFormData.db_type !== 'sqlite' && (
                      <>
                        <input
                          type="text"
                          placeholder="Host"
                          value={dbFormData.host}
                          onChange={e => setDbFormData({...dbFormData, host: e.target.value})}
                          required
                          className="w-full bg-foreground/5 border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="text"
                            placeholder="User"
                            value={dbFormData.username}
                            onChange={e => setDbFormData({...dbFormData, username: e.target.value})}
                            required
                            className="w-full bg-foreground/5 border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                          />
                          <input
                            type="password"
                            placeholder="Password"
                            value={dbFormData.password}
                            onChange={e => setDbFormData({...dbFormData, password: e.target.value})}
                            required
                            className="w-full bg-foreground/5 border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                          />
                        </div>
                      </>
                    )}

                    <input
                      type="text"
                      placeholder={dbFormData.db_type === 'sqlite' ? 'Path (e.g. d:\\db.sqlite)' : 'DB Name'}
                      value={dbFormData.db_name}
                      onChange={e => setDbFormData({...dbFormData, db_name: e.target.value})}
                      required
                      className="w-full bg-foreground/5 border border-border rounded-lg px-3 py-2 text-xs font-mono text-foreground focus:outline-none"
                    />

                    {connectError && (
                      <p className="text-[9px] font-mono text-red-400">{connectError}</p>
                    )}

                    <button
                      type="submit"
                      disabled={connectLoading}
                      className="w-full py-2 bg-cyber-cyan text-black font-mono font-bold text-xs uppercase tracking-widest rounded-lg disabled:opacity-30"
                    >
                      {connectLoading ? 'Saving...' : 'Secure Node'}
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

// Collapsible helper details card for intermediate steps
function ExpandableDetails({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4 border border-border bg-foreground/[0.01] rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-foreground/[0.02] transition-colors"
      >
        <span className="text-[10px] font-mono font-bold text-muted uppercase tracking-widest flex items-center gap-2">
          <BookOpen size={12} className="text-cyber-cyan" /> {title}
        </span>
        <ChevronDown size={14} className={cn("text-muted transition-transform", open && "transform rotate-180")} />
      </button>

      {open && (
        <div className="p-4 border-t border-border animate-in slide-in-from-top-1 duration-200">
          {children}
        </div>
      )}
    </div>
  );
}

function SuggestChip({ label, onClick }) {
  return (
    <button 
      type="button"
      onClick={onClick}
      className="px-3.5 py-1.5 rounded-full border border-border bg-foreground/[0.01] text-[10px] font-mono text-cyber-cyan hover:bg-cyber-cyan/10 hover:border-cyber-cyan/20 transition-all uppercase tracking-widest whitespace-nowrap"
    >
      "{label}"
    </button>
  );
}