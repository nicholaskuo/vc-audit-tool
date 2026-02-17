import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useValuation } from '../hooks/useValuation';
import { ReportView } from '../components/report/ReportView';

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const { loading, error, report, loadReport, reweight } = useValuation();

  useEffect(() => {
    if (id) loadReport(id);
  }, [id, loadReport]);

  const handleReweight = async (weights: Record<string, number>) => {
    if (id) await reweight(id, weights);
  };

  if (loading && !report) {
    return <div className="text-slate-500">Loading report...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  if (!report) {
    return <div className="text-slate-500">Report not found.</div>;
  }

  return (
    <ReportView
      report={report}
      onReweight={handleReweight}
      reweightLoading={loading}
    />
  );
}
