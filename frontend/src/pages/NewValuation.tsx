import { useNavigate } from 'react-router-dom';
import { ValuationForm } from '../components/input/ValuationForm';
import { PipelineTracker } from '../components/progress/PipelineTracker';
import { useValuation } from '../hooks/useValuation';

interface NewValuationProps {
  onValuationCreated?: () => void;
}

export function NewValuation({ onValuationCreated }: NewValuationProps) {
  const navigate = useNavigate();
  const { loading, error, pipelineEvents, submitAsync } = useValuation();

  const handleSubmit = async (data: Parameters<typeof submitAsync>[0]) => {
    const result = await submitAsync(data);
    if (result?.id) {
      onValuationCreated?.();
      navigate(`/report/${result.id}`);
    }
  };

  return (
    <div className="flex gap-8">
      <div className="flex-1">
        <h2 className="text-xl font-bold text-slate-900 mb-6">New Valuation</h2>
        <ValuationForm onSubmit={handleSubmit} loading={loading} />
        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>
      {loading && (
        <div className="w-64">
          <PipelineTracker steps={pipelineEvents} loading={loading} />
        </div>
      )}
    </div>
  );
}
