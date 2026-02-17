import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { ValuationSummary } from '../../types';

interface SidebarProps {
  history: ValuationSummary[];
  loading: boolean;
}

function formatCurrency(value?: number) {
  if (value == null) return '—';
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toLocaleString()}`;
}

export function Sidebar({ history, loading }: SidebarProps) {
  const [search, setSearch] = useState('');

  const filtered = search
    ? history.filter((item) =>
        item.company_name.toLowerCase().includes(search.toLowerCase())
      )
    : history;

  return (
    <aside className="w-64 bg-slate-50 border-r border-slate-200 p-4 overflow-y-auto">
      <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Recent Valuations
      </h2>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Filter by company..."
        className="w-full mb-3 px-2 py-1.5 text-sm border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
      />
      {loading && <p className="text-sm text-slate-400">Loading...</p>}
      {!loading && history.length === 0 && (
        <p className="text-sm text-slate-400">No valuations yet</p>
      )}
      {!loading && history.length > 0 && filtered.length === 0 && (
        <p className="text-sm text-slate-400">No matches</p>
      )}
      <ul className="space-y-2">
        {filtered.map((item) => (
          <li key={item.id}>
            <Link
              to={`/report/${item.id}`}
              className="block p-2 rounded hover:bg-slate-200 transition-colors"
            >
              <div className="text-sm font-medium text-slate-800 truncate">
                {item.company_name}
              </div>
              <div className="text-xs text-slate-500 flex justify-between">
                <span>{formatCurrency(item.fair_value)}</span>
                <span>
                  {item.created_at
                    ? new Date(item.created_at).toLocaleDateString()
                    : ''}
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}
