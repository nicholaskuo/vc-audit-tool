import { useCallback, useState } from 'react';
import type { FinancialProjections } from '../../types';
import { api } from '../../api/client';

interface ProjectionsInputProps {
  value: FinancialProjections;
  onChange: (proj: FinancialProjections) => void;
}

export function ProjectionsInput({ value, onChange }: ProjectionsInputProps) {
  const years = value.revenue_projections.length;
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [uploading, setUploading] = useState(false);

  const updateRevenue = (idx: number, val: string) => {
    const nums = [...value.revenue_projections];
    nums[idx] = parseFloat(val) || 0;
    onChange({ ...value, revenue_projections: nums });
  };

  const updateMargin = (idx: number, val: string) => {
    const nums = [...value.ebitda_margins];
    nums[idx] = parseFloat(val) || 0;
    onChange({ ...value, ebitda_margins: nums });
  };

  const addYear = () => {
    onChange({
      ...value,
      revenue_projections: [...value.revenue_projections, 0],
      ebitda_margins: [...value.ebitda_margins, value.ebitda_margins[value.ebitda_margins.length - 1] || 0.2],
    });
  };

  const removeYear = () => {
    if (years <= 1) return;
    onChange({
      ...value,
      revenue_projections: value.revenue_projections.slice(0, -1),
      ebitda_margins: value.ebitda_margins.slice(0, -1),
    });
  };

  const handleFileUpload = useCallback(async (file: File) => {
    setUploadStatus(null);
    setUploading(true);
    try {
      const proj = await api.uploadProjections(file);
      onChange(proj);
      setUploadStatus({ type: 'success', message: `Loaded ${proj.revenue_projections.length} years of projections` });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setUploadStatus({ type: 'error', message });
    } finally {
      setUploading(false);
    }
  }, [onChange]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  }, [handleFileUpload]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  }, [handleFileUpload]);

  return (
    <div className="space-y-3">
      {/* File upload drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className={`border-2 border-dashed rounded-lg p-4 text-center text-sm transition-colors cursor-pointer ${
          uploading
            ? 'border-blue-400 bg-blue-50/50 text-blue-600'
            : 'border-slate-300 text-slate-500 hover:border-blue-400 hover:bg-blue-50/50'
        }`}
      >
        <label className="cursor-pointer">
          {uploading ? (
            <span>Uploading...</span>
          ) : (
            <>
              <span>Drop .json or .csv file here, or </span>
              <span className="text-blue-600 underline">browse</span>
            </>
          )}
          <input
            type="file"
            accept=".json,.csv"
            onChange={handleFileInput}
            className="hidden"
            disabled={uploading}
          />
        </label>
      </div>

      {uploadStatus && (
        <div className={`text-sm px-3 py-2 rounded ${
          uploadStatus.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {uploadStatus.message}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="pr-4 py-1">Year</th>
              <th className="pr-4 py-1">Revenue ($M)</th>
              <th className="pr-4 py-1">EBITDA Margin (%)</th>
            </tr>
          </thead>
          <tbody>
            {value.revenue_projections.map((rev, i) => (
              <tr key={i}>
                <td className="pr-4 py-1 text-slate-600">Year {i + 1}</td>
                <td className="pr-4 py-1">
                  <input
                    type="number"
                    value={rev || ''}
                    onChange={(e) => updateRevenue(i, e.target.value)}
                    className="w-32 border border-slate-300 rounded px-2 py-1"
                    placeholder="0"
                  />
                </td>
                <td className="pr-4 py-1">
                  <input
                    type="number"
                    step="0.01"
                    value={value.ebitda_margins[i] || ''}
                    onChange={(e) => updateMargin(i, e.target.value)}
                    className="w-32 border border-slate-300 rounded px-2 py-1"
                    placeholder="0.20"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={addYear}
          className="text-sm px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300"
        >
          + Add Year
        </button>
        {years > 1 && (
          <button
            type="button"
            onClick={removeYear}
            className="text-sm px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300"
          >
            - Remove Year
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-3">
        <label className="block">
          <span className="text-sm text-slate-600">WACC</span>
          <input
            type="number"
            step="0.01"
            value={value.wacc}
            onChange={(e) => onChange({ ...value, wacc: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded px-2 py-1 mt-1"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">Terminal Growth Rate</span>
          <input
            type="number"
            step="0.01"
            value={value.terminal_growth_rate}
            onChange={(e) => onChange({ ...value, terminal_growth_rate: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded px-2 py-1 mt-1"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">Tax Rate</span>
          <input
            type="number"
            step="0.01"
            value={value.tax_rate}
            onChange={(e) => onChange({ ...value, tax_rate: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded px-2 py-1 mt-1"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">CapEx % of Revenue</span>
          <input
            type="number"
            step="0.01"
            value={value.capex_percent}
            onChange={(e) => onChange({ ...value, capex_percent: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded px-2 py-1 mt-1"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">NWC Change % of Revenue</span>
          <input
            type="number"
            step="0.01"
            value={value.nwc_change_percent}
            onChange={(e) => onChange({ ...value, nwc_change_percent: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded px-2 py-1 mt-1"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">D&A % of Revenue</span>
          <input
            type="number"
            step="0.01"
            value={value.depreciation_percent}
            onChange={(e) => onChange({ ...value, depreciation_percent: parseFloat(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded px-2 py-1 mt-1"
          />
        </label>
      </div>
    </div>
  );
}
