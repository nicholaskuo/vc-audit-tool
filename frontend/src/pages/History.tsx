import { useNavigate } from 'react-router-dom';
import { useHistory } from '../hooks/useHistory';

function formatCurrency(value?: number): string {
  if (value == null) return '—';
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  return `$${value.toLocaleString()}`;
}

interface HistoryProps {
  onHistoryChanged?: () => void;
}

export function History({ onHistoryChanged }: HistoryProps) {
  const navigate = useNavigate();
  const { history, loading, remove, refresh } = useHistory();

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this valuation?')) {
      await remove(id);
      onHistoryChanged?.();
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-slate-900">Valuation History</h2>
        <button
          onClick={refresh}
          className="text-sm px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-md border border-slate-300"
        >
          Refresh
        </button>
      </div>

      {loading && <p className="text-slate-400">Loading...</p>}

      {!loading && history.length === 0 && (
        <p className="text-slate-500">No valuations found. Create one to get started.</p>
      )}

      {history.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Fair Value</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => navigate(`/report/${item.id}`)}
                  className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {item.company_name}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(item.fair_value)}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={(e) => handleDelete(item.id, e)}
                      className="text-red-400 hover:text-red-600 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
