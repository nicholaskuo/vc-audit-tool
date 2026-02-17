import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { NewValuation } from './pages/NewValuation';
import { ReportDetail } from './pages/ReportDetail';
import { History } from './pages/History';
import { useHistory } from './hooks/useHistory';

function AppLayout() {
  const { history, loading, refresh: refreshHistory } = useHistory();

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar history={history} loading={loading} />
        <main className="flex-1 overflow-y-auto p-6 bg-slate-100">
          <Routes>
            <Route path="/" element={<NewValuation onValuationCreated={refreshHistory} />} />
            <Route path="/report/:id" element={<ReportDetail />} />
            <Route path="/history" element={<History onHistoryChanged={refreshHistory} />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
