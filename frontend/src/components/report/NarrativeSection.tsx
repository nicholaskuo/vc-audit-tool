interface NarrativeSectionProps {
  narrative: string;
}

export function NarrativeSection({ narrative }: NarrativeSectionProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Valuation Narrative
      </h3>
      <div className="prose prose-sm prose-slate max-w-none whitespace-pre-wrap">
        {narrative}
      </div>
    </div>
  );
}
