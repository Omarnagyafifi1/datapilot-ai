import { useState, useEffect } from 'react';
import QueryInput from './components/QueryInput';
import SQLViewer from './components/SQLViewer';
import ResultsTable from './components/ResultsTable';
import InsightBox from './components/InsightBox';
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
    setLoading(true);
    setError(null);
    try {
      const resp = await queryService.generate(q, selectedSourceId);
      setGeneratedSQL(resp.sql || '');
      setEditedSQL(resp.sql || '');
      setInsights(resp.insights || []);
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
          <QueryInput value={question} onChange={setQuestion} onPreview={() => handlePreview(question)} loading={loading} disabled={!selectedSourceId} />
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
          <ResultsTable data={results} loading={loading} />
        </section>

        <section>
          {error && <ErrorMessage reason={error} />}
          <InsightBox insights={insights} error={error} />
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
