import { useState } from 'react';
import type { CompsResult, CompanyFinancials } from '../../types';
import { WarningWithSources } from './WarningWithSources';

interface CompsSectionProps {
  result: CompsResult;
  comparables?: CompanyFinancials[];
}

function fmt(val?: number): string {
  if (val == null) return '—';
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  return val.toFixed(2);
}

function DataSourceBadge({ comp }: { comp: CompanyFinancials }) {
  const isLive = comp.data_source === 'live_yfinance';
  const label = isLive ? 'Live' : comp.data_source === 'mock' ? 'Mock' : 'Unknown';
  const color = isLive
    ? 'bg-green-100 text-green-700'
    : 'bg-amber-100 text-amber-700';
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${color}`}>
      {label}
      {comp.fetched_at && (
        <span className="ml-1 opacity-70">
          {new Date(comp.fetched_at).toLocaleDateString()}
        </span>
      )}
    </span>
  );
}

export function CompsSection({ result, comparables }: CompsSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [showScoring, setShowScoring] = useState(false);
  const hasEstimatedRevenue = result.warnings.some(w => w.toLowerCase().includes('llm estimate'));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-slate-800">Comparable Company Analysis</h3>
          {hasEstimatedRevenue && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
              &#9888; Estimated Revenue
            </span>
          )}
          <p className="w-full text-sm text-slate-500">
            EV: {fmt(result.enterprise_value)} | {result.comparable_count} comps | Median EV/Rev: {result.ev_to_revenue_median.toFixed(1)}x
          </p>
        </div>
        <span className="text-slate-400">{expanded ? '−' : '+'}</span>
      </button>
      {expanded && (
        <div className="px-6 pb-4 space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Median EV/Revenue:</span>{' '}
              <span className="font-medium">{result.ev_to_revenue_median.toFixed(2)}x</span>
            </div>
            <div>
              <span className="text-slate-500">Mean EV/Revenue:</span>{' '}
              <span className="font-medium">{result.ev_to_revenue_mean.toFixed(2)}x</span>
            </div>
            {result.ev_to_ebitda_median != null && (
              <div>
                <span className="text-slate-500">Median EV/EBITDA:</span>{' '}
                <span className="font-medium">{result.ev_to_ebitda_median.toFixed(2)}x</span>
              </div>
            )}
          </div>

          {comparables && comparables.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-100">
                    <th className="py-2 pr-4">Ticker</th>
                    <th className="py-2 pr-4">Name</th>
                    <th className="py-2 pr-4">Revenue</th>
                    <th className="py-2 pr-4">EV</th>
                    <th className="py-2 pr-4">EV/Revenue</th>
                    <th className="py-2 pr-4">EV/EBITDA</th>
                    <th className="py-2 pr-4">Market Cap</th>
                    <th className="py-2">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {comparables.map((c) => (
                    <tr key={c.ticker} className="border-b border-slate-50">
                      <td className="py-2 pr-4 font-medium">
                        {c.data_source_url ? (
                          <a
                            href={c.data_source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
                          >
                            {c.ticker}
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        ) : (
                          c.ticker
                        )}
                      </td>
                      <td className="py-2 pr-4 text-slate-600">{c.name || '—'}</td>
                      <td className="py-2 pr-4">
                        {c.data_source_url ? (
                          <a
                            href={`${c.data_source_url}/financials`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {fmt(c.revenue)}
                          </a>
                        ) : (
                          fmt(c.revenue)
                        )}
                      </td>
                      <td className="py-2 pr-4">
                        {c.data_source_url ? (
                          <a
                            href={`${c.data_source_url}/financials`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {fmt(c.enterprise_value)}
                          </a>
                        ) : (
                          fmt(c.enterprise_value)
                        )}
                      </td>
                      <td className="py-2 pr-4">{c.ev_to_revenue?.toFixed(1) ?? '—'}x</td>
                      <td className="py-2 pr-4">{c.ev_to_ebitda?.toFixed(1) ?? '—'}x</td>
                      <td className="py-2 pr-4">{fmt(c.market_cap)}</td>
                      <td className="py-2"><DataSourceBadge comp={c} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Selection Scoring sub-section */}
          {result.comp_selection_scores && result.comp_selection_scores.length > 0 && (
            <div className="border-t border-slate-100 pt-3">
              <button
                onClick={() => setShowScoring(!showScoring)}
                className="text-sm font-medium text-slate-700 hover:text-slate-900 flex items-center gap-1"
              >
                <span>{showScoring ? '−' : '+'}</span>
                Selection Scoring ({result.comp_selection_scores.length} candidates)
              </button>
              {showScoring && (
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-slate-500 border-b border-slate-100">
                        <th className="py-1.5 pr-3">Ticker</th>
                        <th className="py-1.5 pr-3">Status</th>
                        <th className="py-1.5 pr-3">Sector</th>
                        <th className="py-1.5 pr-3">Size</th>
                        <th className="py-1.5 pr-3">Data Quality</th>
                        <th className="py-1.5 pr-3">Composite</th>
                        <th className="py-1.5">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.comp_selection_scores.map((s) => (
                        <tr key={s.ticker} className={`border-b border-slate-50 ${!s.included ? 'opacity-60' : ''}`}>
                          <td className="py-1.5 pr-3 font-medium">{s.ticker}</td>
                          <td className="py-1.5 pr-3">
                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                              s.included
                                ? 'bg-green-100 text-green-700'
                                : 'bg-red-100 text-red-600'
                            }`}>
                              {s.included ? 'Included' : 'Excluded'}
                            </span>
                          </td>
                          <td className="py-1.5 pr-3">{s.sector_score.toFixed(2)}</td>
                          <td className="py-1.5 pr-3">{s.size_proximity_score.toFixed(2)}</td>
                          <td className="py-1.5 pr-3">{s.data_quality_score.toFixed(2)}</td>
                          <td className="py-1.5 pr-3 font-medium">{s.composite_score.toFixed(2)}</td>
                          <td className="py-1.5 text-slate-500">{s.exclusion_reason || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {result.warnings.length > 0 && (
            <div className="space-y-1">
              {result.warnings.map((w, i) => (
                <WarningWithSources key={i} text={w} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
