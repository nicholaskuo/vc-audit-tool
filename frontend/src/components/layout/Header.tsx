import { Link } from 'react-router-dom';

export function Header() {
  return (
    <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold tracking-tight">
        Modus: VC Audit Tool
      </Link>
      <nav className="flex gap-4 text-sm">
        <Link to="/" className="hover:text-blue-300 transition-colors">
          New Valuation
        </Link>
        <Link to="/history" className="hover:text-blue-300 transition-colors">
          History
        </Link>
      </nav>
    </header>
  );
}
