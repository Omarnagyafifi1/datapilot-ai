import React, { useState, useEffect } from 'react';
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

  useEffect(() => {
    if (!selectedSourceId) {
      setExamples(COPY.EMPTY_QUERY_EXAMPLES);
      return;
    }
    api.schema.get(selectedSourceId)
      .then(resp => {
        if (resp.data && resp.data.success) {
          const schemaData = resp.data.data;
          const tables = schemaData.tables || [];
          const tableNames = tables.map(t => String(t.name || t).toLowerCase());
          
          let prompts = [];
          if (tableNames.includes('employees')) {
            prompts.push("Show all employees and their salaries");
            prompts.push("ما هو إجمالي الرواتب لكل قسم؟");
            prompts.push("من هم أعلى 5 موظفين راتباً؟");
          }
          if (tableNames.includes('sales')) {
            prompts.push("Show total sales revenue by category");
            prompts.push("أظهر المبيعات الإجمالية حسب الفئة بالعربية");
            prompts.push("What were total sales by month in 2025?");
          }
          if (tableNames.includes('inventory')) {
            prompts.push("Which products are below reorder level?");
            prompts.push("عرض المنتجات التي نفد مخزونها");
          }
          
          // Fallback if not enough prompts
          if (prompts.length < 3) {
            tables.forEach(t => {
              const name = t.name || t;
              if (prompts.length < 3 && name) {
                prompts.push(`Show first 10 rows from ${name}`);
              }
            });
          }
          
          if (prompts.length === 0) {
            prompts = COPY.EMPTY_QUERY_EXAMPLES;
          }
          setExamples(prompts.slice(0, 4));
        }
      })
      .catch(err => {
        console.error("Failed to load schema for examples", err);
        setExamples(COPY.EMPTY_QUERY_EXAMPLES);
      });
  }, [selectedSourceId]);

  const handlePreview = async (q) => {
    if (!q || !selectedSourceId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await queryService.generate(q, selectedSourceId);
      setGeneratedSQL(resp.sql || '');
      setEditedSQL(resp.sql || '');
      setInsights(resp.insights || []);
      if (resp.results) setResults(resp.results || []);
      setPhase('preview');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to generate SQL');
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
      const resp = await queryService.execute(sql, selectedSourceId);
      setResults(resp.results || []);
      setInsights(resp.insights || []);
      setPhase('executed');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to execute SQL');
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
            <SQLViewer sql={editedSQL} onChange={setEditedSQL} onExecute={() => setConfirmOpen(true)} loading={loading} />
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
      />
    </div>
  );
}
