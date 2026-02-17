import { useState } from 'react';
import type { PipelineStep, LLMCallLog } from '../../types';

interface AuditTrailProps {
  steps: PipelineStep[];
  llmCalls: LLMCallLog[];
}

const STEP_DESCRIPTIONS: Record<string, string> = {
  research: 'Searches the web for company financials, sector data, comparable companies, and funding history.',
  research_fallback: 'Fallback research using LLM knowledge (web search was unavailable).',
  enrich: 'Structures raw research into sector classification, comparable tickers, estimated financials, and applicable valuation methods.',
  narrate: 'Generates an auditor-facing narrative summarizing the valuation methodology, key assumptions, and results.',
};

function getStepDescription(stepName: string): string {
  return STEP_DESCRIPTIONS[stepName] || `LLM call for the "${stepName}" pipeline stage.`;
}

export function AuditTrail({ steps, llmCalls }: AuditTrailProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedLog, setSelectedLog] = useState<number | null>(null);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between text-left"
      >
        <h3 className="font-semibold text-slate-800">Audit Trail</h3>
        <span className="text-slate-400">{expanded ? '−' : '+'}</span>
      </button>
      {expanded && (
        <div className="px-6 pb-4 space-y-4">
          {/* Pipeline steps */}
          <div>
            <h4 className="text-sm font-medium text-slate-600 mb-2">Pipeline Steps</h4>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-100">
                  <th className="py-1.5 pr-4">Step</th>
                  <th className="py-1.5 pr-4">Status</th>
                  <th className="py-1.5 pr-4">Duration</th>
                  <th className="py-1.5">Error</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((s, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td className="py-1.5 pr-4">{s.step_name}</td>
                    <td className="py-1.5 pr-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs ${
                          s.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : s.status === 'failed'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {s.status}
                      </span>
                    </td>
                    <td className="py-1.5 pr-4 text-slate-500">
                      {s.duration_ms != null ? `${Math.round(s.duration_ms)}ms` : '—'}
                    </td>
                    <td className="py-1.5 text-red-500 text-xs">{s.error || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* LLM call logs */}
          {llmCalls.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-600 mb-2">LLM Calls</h4>
              <div className="space-y-2">
                {llmCalls.map((log, i) => (
                  <div key={i} className="border border-slate-100 rounded-lg">
                    <button
                      onClick={() => setSelectedLog(selectedLog === i ? null : i)}
                      className="w-full px-4 py-2 flex items-center justify-between text-left text-sm"
                    >
                      <div>
                        <span className="font-medium">{log.step_name}</span>
                        <span className="text-slate-400 ml-2">
                          {log.model} | {log.tokens_used ?? '?'} tokens | {Math.round(log.duration_ms ?? 0)}ms
                        </span>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {getStepDescription(log.step_name)}
                        </p>
                      </div>
                      <span className="text-slate-400 shrink-0 ml-2">{selectedLog === i ? '−' : '+'}</span>
                    </button>
                    {selectedLog === i && (
                      <div className="px-4 pb-3 text-xs">
                        <div className="font-medium text-slate-500 mb-1">Response:</div>
                        <pre className="bg-slate-50 p-2 rounded overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                          {log.response}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
