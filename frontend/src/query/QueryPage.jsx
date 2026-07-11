import { useState, useEffect } from 'react';
import SQLViewer from './components/SQLViewer';
import ConfirmationModal from '../components/ConfirmationModal';
import ErrorMessage from '../components/ErrorMessage';
import EmptyState from '../components/EmptyState';
import { queryService } from '../services/queryService';
import { COPY } from '../lib/copy';
import { api } from '../lib/api';
import { getErrorMessage } from '../lib/utils';

export default function QueryPage({ selectedSourceId, selectedSource }) {
  const [question, setQuestion] = useState('');
  const [generatedSQL, setGeneratedSQL] = useState('');
  const [editedSQL, setEditedSQL] = useState('');
  const [results, setResults] = useState([]);
  const [insights, setInsights] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [phase, setPhase] = useState('idle'); // idle | preview | executed
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [examples, setExamples] = useState(COPY.EMPTY_QUERY_EXAMPLES);
  const [threadId, setThreadId] = useState(null);
  const [requiresApproval, setRequiresApproval] = useState(false);

  useEffect(() => {
    if (!selectedSourceId) {
      setExamples(COPY.EMPTY_QUERY_EXAMPLES);
      return;
    }
    api.schema.suggestions(selectedSourceId)
      .then(resp => {
        if (resp.data && resp.data.success && resp.data.data.length > 0) {
          setExamples(resp.data.data);
        } else {
          setExamples(COPY.EMPTY_QUERY_EXAMPLES);
        }
      })
      .catch(err => {
        console.error("Failed to load schema suggestions", err);
        setExamples(COPY.EMPTY_QUERY_EXAMPLES);
      });
  }, [selectedSourceId]);

  const handlePreview = async (q) => {
    if (!q || !selectedSourceId) return;
    setResults([]);
    setInsights([]);
    setSuggestions([]);
    setLoading(true);
    setError(null);
    try {
      const resp = await queryService.generate(q, selectedSourceId);
      setGeneratedSQL(resp.sql || '');
      setEditedSQL(resp.sql || '');
      setInsights(resp.insights || []);
      setSuggestions(resp.suggestions || []);
      setRequiresApproval(resp.requiresApproval || false);
      setThreadId(resp.threadId || null);
      if (resp.results) setResults(resp.results || []);
      setPhase('preview');
    } catch (e) {
      setError(getErrorMessage(e, 'Failed to generate SQL'));
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async (sql) => {
    if (!sql || !selectedSourceId) return;
    setConfirmOpen(false);
    setLoading(true);
    setError(null);
    try {
      const tid = requiresApproval ? threadId : null;
      const resp = requiresApproval
        ? await queryService.approve(tid, true)
        : await queryService.execute(question, sql, selectedSourceId, tid);
      setResults(resp.results || []);
      setInsights(resp.insights || []);
      setSuggestions(resp.suggestions || []);
      setRequiresApproval(resp.requiresApproval || false);
      setThreadId(resp.threadId || null);
      setPhase('executed');
    } catch (e) {
      setError(getErrorMessage(e, 'Failed to execute SQL'));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExample = (exampleText) => {
    setQuestion(exampleText);
    handlePreview(exampleText);
  };

  return (
    <div className="p-12">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h2 className="text-2xl font-bold mb-2">Query</h2>
          <p className="text-sm text-muted">Ask a question about your data, review the generated SQL, execute it, and inspect results.</p>
        </div>

        <section className="space-y-4">
          <div className="glass rounded-2xl border-border p-4 space-y-3">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your data..."
              disabled={!selectedSourceId}
              className="w-full min-h-[80px] bg-black/40 font-mono text-xs text-foreground/80 p-4 rounded resize-vertical border-border"
            />
            <button
              onClick={() => handlePreview(question)}
              disabled={loading || !question.trim() || !selectedSourceId}
              className="py-2.5 px-6 bg-cyber-cyan text-background font-mono font-bold text-xs uppercase rounded-lg hover:brightness-105 disabled:opacity-40 transition-all flex items-center gap-2"
            >
              {loading ? COPY.LOADING_GENERATING : COPY.PREVIEW_SQL}
            </button>
          </div>
        </section>

        <section className="space-y-4">
          {phase === 'idle' && !generatedSQL ? (
            <EmptyState 
              title="Ready to ask a question" 
              examples={examples} 
              onSelectExample={handleSelectExample} 
            />
          ) : (
            <SQLViewer
              sql={editedSQL}
              onChange={setEditedSQL}
              onRun={() => handleExecute(editedSQL)}
              onRequestApproval={() => setConfirmOpen(true)}
              loading={loading}
              requiresApproval={requiresApproval}
            />
          )}
        </section>

        <section className="space-y-4">
          {results.length > 0 ? (
            <div className="glass rounded-2xl border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-foreground/5">
                      {Object.keys(results[0] || {}).map((key) => (
                        <th key={key} className="px-4 py-3 font-semibold text-foreground/60 border-b border-border uppercase text-[10px] tracking-wider">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {results.map((row, i) => (
                      <tr key={i} className="hover:bg-foreground/[0.02] transition-colors">
                        {Object.keys(row).map((key) => (
                          <td key={key} className="px-4 py-3 text-foreground/80 whitespace-nowrap">{String(row[key] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="glass p-6 rounded-2xl border-border text-center text-sm text-muted">{COPY.NO_RESULTS}</div>
          )}
        </section>

        <section>
          {error && <ErrorMessage reason={error} />}
          {insights.length > 0 && (
            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-2 text-[10px] font-bold text-foreground/40 uppercase tracking-widest">
                AI Insights
              </div>
              <div className="space-y-2">
                {insights.map((item, i) => {
                  const isObj = typeof item === 'object' && item !== null;
                  const enText = isObj ? (item.en || '') : String(item);
                  const arText = isObj ? (item.ar || '') : '';
                  return (
                    <div key={i} className="glass p-4 rounded-xl border-border">
                      {enText && <div className="text-sm text-foreground/80 leading-relaxed">{enText}</div>}
                      {arText && <div className="text-sm text-cyber-cyan/95 leading-relaxed text-right" dir="rtl">{arText}</div>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {suggestions.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-[10px] font-bold text-foreground/40 uppercase tracking-widest">
                Next Steps
              </div>
              <div className="space-y-2">
                {suggestions.map((item, i) => {
                  const isObj = typeof item === 'object' && item !== null;
                  const enText = isObj ? (item.en || '') : String(item);
                  const arText = isObj ? (item.ar || '') : '';
                  return (
                    <div key={i} className="glass p-4 rounded-xl border-border">
                      {enText && <div className="text-sm text-foreground/80 leading-relaxed">{enText}</div>}
                      {arText && <div className="text-sm text-cyber-cyan/95 leading-relaxed text-right" dir="rtl">{arText}</div>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>
      </div>

      <ConfirmationModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => handleExecute(editedSQL)}
        sql={editedSQL}
        source={selectedSource}
        requiresApproval={requiresApproval}
      />
    </div>
  );
}
