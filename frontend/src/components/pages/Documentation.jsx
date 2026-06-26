import React, { useState } from 'react';
import { BookOpen, Code2, Database, Zap, ChevronRight, Terminal, Shield, Cpu, Layers, Binary } from 'lucide-react';

const sections = [
  {
    id: 'overview',
    title: 'System Overview',
    icon: Cpu,
    content: `DataPilot AI is an intelligent Text-to-SQL data analyst system. It converts natural language questions (English & Arabic) into optimized SQL queries, executes them against your connected databases, and returns results with AI-generated insights and visualizations.

The system uses a LangGraph-based agent pipeline with intent routing, schema-aware SQL generation, automatic retry with fix loops, and human-in-the-loop approval for write operations (INSERT, UPDATE, DELETE).`
  },
  {
    id: 'architecture',
    title: 'Architecture',
    icon: Layers,
    content: `The application follows a modular architecture:

• Frontend — React + Vite SPA with cyberpunk-themed UI
• Backend — FastAPI server with RESTful API endpoints
• AI Agent — LangGraph StateGraph with multi-node pipeline:
  ├── Intent Router (classifies: GENERAL / INQUIRE / ADD / UPDATE / DELETE)
  ├── Schema Fetcher (retrieves & filters relevant schema context)
  ├── SQL Generator (LLM-powered, dialect-aware)
  ├── Execution Engine (runs SQL via SQLAlchemy)
  ├── Validation Node (verifies results match the question)
  ├── Fix/Retry Loop (auto-corrects failed queries, up to 3 retries)
  ├── Visualization Generator (Plotly chart specs)
  ├── Insight & Suggestion Generator (bilingual AR/EN)
  └── Long-term Memory (per-user query history via InMemoryStore)
• Database Support — SQLite, PostgreSQL, MySQL, MSSQL, Oracle`
  },
  {
    id: 'features',
    title: 'Key Features',
    icon: Zap,
    content: `• Bilingual Support — Ask questions in English or Arabic
• Multi-Database — Connect to SQLite, PostgreSQL, MySQL, SQL Server, Oracle
• Smart Query Generation — Context-aware SQL with schema filtering
• Auto-Retry — Failed queries are automatically fixed and retried
• Write Protection — INSERT/UPDATE/DELETE require human approval
• Visualizations — Auto-generated charts from query results
• Export — CSV export, SVG/PNG charts, Markdown reports
• Query History — Full audit trail with latency tracking
• Schema Explorer — Interactive database schema viewer
• CSV Upload — Upload CSV files to create queryable tables`
  },
];

const endpoints = [
  { method: 'POST', path: '/api/query', desc: 'Submit a natural language question → AI generates SQL → executes → returns results with insights' },
  { method: 'POST', path: '/api/query/approval', desc: 'Approve or reject a pending write operation (INSERT/UPDATE/DELETE)' },
  { method: 'POST', path: '/api/query/page', desc: 'Paginate through query results (sql, source_id, page, page_size)' },
  { method: 'GET',  path: '/api/datasources', desc: 'List all registered data source connections' },
  { method: 'POST', path: '/api/datasources/connect', desc: 'Register a new database connection (name, db_type, host, port, db_name, username, password)' },
  { method: 'DELETE', path: '/api/datasources/:id', desc: 'Remove a data source connection' },
  { method: 'GET',  path: '/api/datasources/:id/schema', desc: 'Fetch the schema (tables & columns) for a connected data source' },
  { method: 'GET',  path: '/api/datasources/:id/suggestions', desc: 'Get AI-powered query suggestions based on the schema' },
  { method: 'GET',  path: '/api/query-history', desc: 'Retrieve the full query execution history' },
  { method: 'GET',  path: '/api/system/stats', desc: 'System statistics: total sources, queries, avg latency, success rate' },
  { method: 'GET',  path: '/api/system/feed', desc: 'Activity feed of recent system events' },
  { method: 'POST', path: '/api/data/csv', desc: 'Upload a CSV file to ingest into the database' },
  { method: 'POST', path: '/api/explain', desc: 'Get a lightweight explanation of a SQL query' },
  { method: 'POST', path: '/api/report/generate', desc: 'Generate a downloadable Markdown report from query results' },
  { method: 'GET',  path: '/api/health', desc: 'Health check endpoint' },
];

const methodColor = {
  GET: 'text-cyber-lime bg-cyber-lime/10 border-cyber-lime/20',
  POST: 'text-cyber-cyan bg-cyber-cyan/10 border-cyber-cyan/20',
  DELETE: 'text-red-400 bg-red-400/10 border-red-400/20',
  PUT: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
};

export function Documentation() {
  const [activeSection, setActiveSection] = useState('overview');

  return (
    <div className="p-12 max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="mb-12">
        <div className="flex items-center gap-2 text-cyber-cyan mb-4">
          <BookOpen size={20} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest">Knowledge Base</span>
        </div>
        <h2 className="text-4xl font-extrabold tracking-tighter mb-4">
          DOCUMENTATION<br /><span className="text-muted">.REFERENCE</span>
        </h2>
        <p className="text-muted max-w-xl text-sm leading-relaxed">
          Comprehensive guide to the DataPilot AI system architecture, features, and API reference.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Section Navigation */}
        <div className="lg:col-span-1 space-y-2">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left ${
                activeSection === section.id
                  ? 'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20'
                  : 'text-white/50 hover:bg-white/5 hover:text-white'
              }`}
            >
              <section.icon size={16} />
              <span className="text-xs font-mono uppercase tracking-wider">{section.title}</span>
            </button>
          ))}
          <button
            onClick={() => setActiveSection('api')}
            className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left ${
              activeSection === 'api'
                ? 'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20'
                : 'text-white/50 hover:bg-white/5 hover:text-white'
            }`}
          >
            <Code2 size={16} />
            <span className="text-xs font-mono uppercase tracking-wider">API Reference</span>
          </button>
          <button
            onClick={() => setActiveSection('db')}
            className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left ${
              activeSection === 'db'
                ? 'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20'
                : 'text-white/50 hover:bg-white/5 hover:text-white'
            }`}
          >
            <Database size={16} />
            <span className="text-xs font-mono uppercase tracking-wider">Databases</span>
          </button>
        </div>

        {/* Section Content */}
        <div className="lg:col-span-3">
          {sections.map((section) =>
            activeSection === section.id ? (
              <div key={section.id} className="glass p-8 rounded-2xl border-white/5 animate-in fade-in duration-300">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan">
                    <section.icon size={20} />
                  </div>
                  <h3 className="text-xl font-bold">{section.title}</h3>
                </div>
                <pre className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed font-sans">{section.content}</pre>
              </div>
            ) : null
          )}

          {activeSection === 'api' && (
            <div className="glass p-8 rounded-2xl border-white/5 animate-in fade-in duration-300">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan">
                  <Code2 size={20} />
                </div>
                <h3 className="text-xl font-bold">API Reference</h3>
              </div>
              <div className="space-y-3">
                {endpoints.map((ep, i) => (
                  <div key={i} className="flex items-start gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.04] transition-colors">
                    <span className={`text-[9px] font-mono font-bold px-2 py-1 rounded border shrink-0 ${methodColor[ep.method]}`}>
                      {ep.method}
                    </span>
                    <div className="min-w-0">
                      <code className="text-xs font-mono text-cyber-cyan break-all">{ep.path}</code>
                      <p className="text-xs text-muted mt-1 leading-relaxed">{ep.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === 'db' && (
            <div className="glass p-8 rounded-2xl border-white/5 animate-in fade-in duration-300">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-cyber-cyan/10 flex items-center justify-center text-cyber-cyan">
                  <Database size={20} />
                </div>
                <h3 className="text-xl font-bold">Supported Databases</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { name: 'SQLite', driver: 'Built-in', port: 'N/A (file-based)', desc: 'Lightweight file-based database, perfect for CSV uploads and local testing.' },
                  { name: 'PostgreSQL', driver: 'psycopg2', port: '5432', desc: 'Advanced open-source RDBMS with full SQL compliance and JSON support.' },
                  { name: 'MySQL', driver: 'pymysql', port: '3306', desc: 'Popular open-source database widely used in web applications.' },
                  { name: 'SQL Server', driver: 'pyodbc (ODBC 17)', port: '1433', desc: 'Microsoft enterprise database with T-SQL support.' },
                  { name: 'Oracle', driver: 'cx_oracle', port: '1521', desc: 'Enterprise-grade Oracle Database with PL/SQL support.' },
                ].map((db) => (
                  <div key={db.name} className="p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                    <h5 className="font-bold text-white mb-2 flex items-center gap-2">
                      <Binary size={14} className="text-cyber-cyan" /> {db.name}
                    </h5>
                    <p className="text-xs text-muted leading-relaxed mb-2">{db.desc}</p>
                    <div className="flex gap-4 text-[10px] font-mono text-white/40">
                      <span>Driver: {db.driver}</span>
                      <span>Port: {db.port}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Documentation;
