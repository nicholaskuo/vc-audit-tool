import { useState } from 'react';
import type { ValuationRequest, FinancialProjections } from '../../types';
import { ProjectionsInput } from './ProjectionsInput';

interface ValuationFormProps {
  onSubmit: (data: ValuationRequest) => void;
  loading: boolean;
}

const defaultProjections: FinancialProjections = {
  revenue_projections: [0, 0, 0, 0, 0],
  ebitda_margins: [0.2, 0.22, 0.24, 0.26, 0.28],
  capex_percent: 0.05,
  nwc_change_percent: 0.02,
  tax_rate: 0.25,
  wacc: 0.12,
  terminal_growth_rate: 0.03,
  depreciation_percent: 0.0,
};

export function ValuationForm({ onSubmit, loading }: ValuationFormProps) {
  const [companyName, setCompanyName] = useState('');
  const [description, setDescription] = useState('');
  const [sector, setSector] = useState('');
  const [revenue, setRevenue] = useState('');
  const [ebitda, setEbitda] = useState('');
  const [tickers, setTickers] = useState('');
  const [dcfMode, setDcfMode] = useState<'na' | 'provide'>('na');
  const [projections, setProjections] = useState<FinancialProjections>(defaultProjections);
  const [lastRoundMode, setLastRoundMode] = useState<'na' | 'provide'>('na');
  const [lastRoundValuation, setLastRoundValuation] = useState('');
  const [lastRoundDate, setLastRoundDate] = useState('');
  const [indexTicker, setIndexTicker] = useState('^IXIC');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) return;

    const data: ValuationRequest = {
      company_name: companyName.trim(),
    };
    if (description) data.description = description;
    if (sector) data.sector = sector;
    if (revenue) data.revenue = parseFloat(revenue);
    if (ebitda) data.ebitda = parseFloat(ebitda);
    if (tickers) {
      data.comparable_tickers = tickers.split(',').map((t) => t.trim()).filter(Boolean);
    }
    if (dcfMode === 'provide' && projections.revenue_projections.some((r) => r > 0)) {
      data.financial_projections = projections;
    }
    if (lastRoundMode === 'provide' && lastRoundValuation && lastRoundDate) {
      data.last_round_valuation = parseFloat(lastRoundValuation);
      data.last_round_date = lastRoundDate;
      data.index_ticker = indexTicker;
    }

    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {/* Required fields */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-800">Company Information</h3>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">
            Company Name <span className="text-red-500">*</span>
          </span>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="w-full mt-1 border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            placeholder="e.g., Acme Analytics"
            required
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full mt-1 border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            rows={2}
            placeholder="Brief description of the company..."
          />
        </label>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Sector</span>
            <input
              type="text"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="w-full mt-1 border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="e.g., SaaS / Enterprise Software"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700 inline-flex items-center gap-1">
              Comparable Tickers
              <span className="relative group">
                <svg className="w-3.5 h-3.5 text-slate-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 bg-slate-800 text-white text-xs rounded-md whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-10">
                  Enter stock tickers separated by commas, e.g. MSFT, CRM, NOW
                </span>
              </span>
            </span>
            <input
              type="text"
              value={tickers}
              onChange={(e) => setTickers(e.target.value)}
              className="w-full mt-1 border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="MSFT, CRM, NOW"
            />
          </label>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Annual Revenue ($)</span>
            <input
              type="number"
              value={revenue}
              onChange={(e) => setRevenue(e.target.value)}
              className="w-full mt-1 border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="50000000"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Annual EBITDA ($)</span>
            <input
              type="number"
              value={ebitda}
              onChange={(e) => setEbitda(e.target.value)}
              className="w-full mt-1 border border-slate-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="10000000"
            />
          </label>
        </div>
      </div>

      {/* DCF Projections */}
      <div className="border border-slate-200 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-medium text-slate-700">DCF Projections</span>
          <div className="flex rounded-md overflow-hidden border border-slate-300 text-sm">
            <button
              type="button"
              onClick={() => setDcfMode('na')}
              className={`px-3 py-1.5 transition-colors ${
                dcfMode === 'na'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              N/A — Model will research
            </button>
            <button
              type="button"
              onClick={() => setDcfMode('provide')}
              className={`px-3 py-1.5 border-l border-slate-300 transition-colors ${
                dcfMode === 'provide'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              Provide my own values
            </button>
          </div>
        </div>
        {dcfMode === 'na' ? (
          <p className="text-sm text-slate-500">
            The model will research and estimate growth rates, margins, WACC, and terminal growth rate from public data.
            Estimated DCF results will be clearly marked and given reduced weight.
          </p>
        ) : (
          <ProjectionsInput value={projections} onChange={setProjections} />
        )}
      </div>

      {/* Last Funding Round */}
      <div className="border border-slate-200 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-medium text-slate-700">Last Funding Round</span>
          <div className="flex rounded-md overflow-hidden border border-slate-300 text-sm">
            <button
              type="button"
              onClick={() => setLastRoundMode('na')}
              className={`px-3 py-1.5 transition-colors ${
                lastRoundMode === 'na'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              N/A — Model will research
            </button>
            <button
              type="button"
              onClick={() => setLastRoundMode('provide')}
              className={`px-3 py-1.5 border-l border-slate-300 transition-colors ${
                lastRoundMode === 'provide'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50'
              }`}
            >
              Provide my own values
            </button>
          </div>
        </div>
        {lastRoundMode === 'na' ? (
          <p className="text-sm text-slate-500">
            The model will search for the most recent funding round data. Estimated last round results
            will be clearly marked and given reduced weight.
          </p>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <label className="block">
                <span className="text-sm text-slate-600">Valuation ($)</span>
                <input
                  type="number"
                  value={lastRoundValuation}
                  onChange={(e) => setLastRoundValuation(e.target.value)}
                  className="w-full mt-1 border border-slate-300 rounded px-2 py-1"
                  placeholder="200000000"
                />
              </label>
              <label className="block">
                <span className="text-sm text-slate-600">Round Date</span>
                <input
                  type="date"
                  value={lastRoundDate}
                  onChange={(e) => setLastRoundDate(e.target.value)}
                  className="w-full mt-1 border border-slate-300 rounded px-2 py-1"
                />
              </label>
            </div>
            <label className="block">
              <span className="text-sm text-slate-600">Index Ticker</span>
              <input
                type="text"
                value={indexTicker}
                onChange={(e) => setIndexTicker(e.target.value)}
                className="w-full mt-1 border border-slate-300 rounded px-2 py-1"
                placeholder="^IXIC"
              />
            </label>
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={loading || !companyName.trim()}
        className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Running Valuation...' : 'Run Valuation'}
      </button>
    </form>
  );
}
