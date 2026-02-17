import type { PipelineStep } from '../../types';

interface PipelineTrackerProps {
  steps: PipelineStep[];
  loading: boolean;
}

const STEP_LABELS: Record<string, string> = {
  validate: 'Validate Input',
  research: 'Research Company (Web Search)',
  enrich: 'Structure Analysis',
  fetch: 'Fetch Market Data',
  valuate: 'Run Valuations',
  narrate: 'Generate Narrative',
  persist: 'Save Report',
};

const SIMULATED_STEPS = ['validate', 'research', 'enrich', 'fetch', 'valuate', 'narrate', 'persist'];

export function PipelineTracker({ steps, loading }: PipelineTrackerProps) {
  const displaySteps: PipelineStep[] = steps.length > 0
    ? steps
    : SIMULATED_STEPS.map((name, i) => ({
        step_name: name,
        status: loading ? (i === 0 ? 'running' : 'pending') : 'pending',
      }));

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
        Pipeline Progress
      </h3>
      <div className="space-y-1">
        {displaySteps.map((step) => (
          <div key={step.step_name} className="flex items-center gap-3 py-1.5">
            <StatusIcon status={step.status} />
            <div className="flex-1">
              <span className="text-sm text-slate-700">
                {STEP_LABELS[step.step_name] || step.step_name}
              </span>
            </div>
            {step.duration_ms != null && (
              <span className="text-xs text-slate-400">
                {step.duration_ms < 1000
                  ? `${Math.round(step.duration_ms)}ms`
                  : `${(step.duration_ms / 1000).toFixed(1)}s`}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <span className="w-5 h-5 rounded-full bg-green-500 text-white flex items-center justify-center text-xs">&#10003;</span>;
    case 'running':
      return <span className="w-5 h-5 rounded-full bg-blue-500 animate-pulse" />;
    case 'failed':
      return <span className="w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center text-xs">!</span>;
    case 'skipped':
      return <span className="w-5 h-5 rounded-full bg-slate-300" />;
    default:
      return <span className="w-5 h-5 rounded-full border-2 border-slate-300" />;
  }
}
