import type { ValuationReport, CompanyFinancials } from '../../types';
import { BlendedSummary } from './BlendedSummary';
import { WeightSliders } from './WeightSliders';
import { CompsSection } from './CompsSection';
import { DCFSection } from './DCFSection';
import { LastRoundSection } from './LastRoundSection';
import { NarrativeSection } from './NarrativeSection';
import { AssumptionsTable, hasModelEstimates } from './AssumptionsTable';
import { AuditTrail } from './AuditTrail';
import { PipelineTracker } from '../progress/PipelineTracker';

interface ReportViewProps {
  report: ValuationReport;
  onReweight: (weights: Record<string, number>) => void;
  reweightLoading: boolean;
}

function DataFreshnessBadge({ comparables }: { comparables: CompanyFinancials[] }) {
  if (comparables.length === 0) return null;

  const first = comparables[0];
  const isLive = first.data_source === 'live_yfinance';
  const label = isLive ? 'Live Data' : first.data_source === 'mock' ? 'Mock Data' : 'Unknown Source';
  const color = isLive
    ? 'bg-green-100 text-green-700 border-green-200'
    : 'bg-amber-100 text-amber-700 border-amber-200';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-green-500' : 'bg-amber-500'}`} />
      {label}
      {first.fetched_at && (
        <span className="opacity-70">
          {new Date(first.fetched_at).toLocaleString()}
        </span>
      )}
    </span>
  );
}

export function ReportView({ report, onReweight, reweightLoading }: ReportViewProps) {
  const bv = report.blended_valuation;

  const comparables: CompanyFinancials[] =
    (report.market_data_summary as { comparables?: CompanyFinancials[] })?.comparables ?? [];

  const showEstimatesFirst = hasModelEstimates(report.assumptions);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-slate-900">{report.company_name}</h1>
        <span className="text-sm text-slate-400">
          {new Date(report.created_at).toLocaleString()}
        </span>
        <DataFreshnessBadge comparables={comparables} />
      </div>

      {/* Error state — shown prominently when valuation failed */}
      {report.error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-red-800 mb-3">
            Valuation Could Not Be Completed
          </h2>
          <p className="text-red-700 text-sm whitespace-pre-line mb-4">
            {report.error.split('\n\n')[0]}
          </p>
          {report.missing_data && report.missing_data.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-red-800">What's missing:</h3>
              <ul className="space-y-2">
                {report.missing_data.map((item, i) => (
                  <li
                    key={i}
                    className="flex gap-2 text-sm text-red-700 bg-red-100/50 rounded-lg p-3"
                  >
                    <span className="text-red-400 mt-0.5 shrink-0">&#9679;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {bv && !report.error ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <BlendedSummary valuation={bv} />
            </div>
            <div>
              <WeightSliders
                weights={bv.methodology_weights}
                onApply={onReweight}
                loading={reweightLoading}
              />
            </div>
          </div>

          {/* Show assumptions prominently before methodology details when estimates exist */}
          {showEstimatesFirst && <AssumptionsTable assumptions={report.assumptions} />}

          {/* Methodology details */}
          <div className="space-y-4">
            {bv.comps_result && (
              <CompsSection result={bv.comps_result} comparables={comparables} />
            )}
            {bv.dcf_result && <DCFSection result={bv.dcf_result} />}
            {bv.last_round_result && <LastRoundSection result={bv.last_round_result} />}
          </div>
        </>
      ) : !report.error ? (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-700">
          No valuation results available. The pipeline may have encountered errors.
        </div>
      ) : null}

      {report.narrative && <NarrativeSection narrative={report.narrative} />}

      {/* Show assumptions at bottom only when no estimates (normal position) */}
      {!showEstimatesFirst && <AssumptionsTable assumptions={report.assumptions} />}

      <PipelineTracker steps={report.pipeline_steps} loading={false} />

      <AuditTrail steps={report.pipeline_steps} llmCalls={report.llm_call_logs} />
    </div>
  );
}
