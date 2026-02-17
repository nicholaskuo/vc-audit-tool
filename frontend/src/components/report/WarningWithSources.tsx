/**
 * Renders a warning string, converting any embedded URLs into clickable links.
 * URLs in warnings follow the format: "Title (https://example.com)"
 */
export function WarningWithSources({ text }: { text: string }) {
  // Split on URL pattern: "Title (https://...)" or bare "https://..."
  const parts = text.split(/(https?:\/\/[^\s,)]+)/g);

  return (
    <p className="text-sm text-amber-600">
      <span className="font-medium">Warning: </span>
      {parts.map((part, i) =>
        part.match(/^https?:\/\//) ? (
          <a
            key={i}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline break-all"
          >
            {part}
          </a>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </p>
  );
}

/**
 * Renders a list of research source links.
 */
export function SourceLinks({ sources }: { sources: { title: string; url: string }[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-1">
      {sources.map((s, i) => (
        <a
          key={i}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 hover:text-blue-900 transition-colors"
        >
          <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          {s.title || new URL(s.url).hostname}
        </a>
      ))}
    </div>
  );
}
