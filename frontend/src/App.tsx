import { useEffect, useState } from 'react';
import type { ComponentType } from 'react';
import { ClipboardCheck, ClipboardList, GraduationCap, LayoutDashboard, Menu, Package, Receipt, Store, Wallet } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import SchoolPage from './pages/SchoolPage';
import PurchasesPage from './pages/PurchasesPage';
import StockPage from './pages/StockPage';
import CashPage from './pages/CashPage';
import ExpensesPage from './pages/ExpensesPage';
import WeeklyReportPage from './pages/WeeklyReportPage';

export type Page = 'overview' | 'school' | 'purchases' | 'stock' | 'cash' | 'expenses' | 'weekly';
const nav: { id: Page; label: string; icon: ComponentType<{ size?: number }>; view: ComponentType<{ navigate: (page: Page) => void }> }[] = [
  { id: 'overview', label: 'Rotina da gestão', icon: LayoutDashboard, view: Dashboard },
  { id: 'school', label: 'Calendário da escola', icon: GraduationCap, view: SchoolPage },
  { id: 'purchases', label: 'Compras e notas', icon: ClipboardList, view: PurchasesPage },
  { id: 'stock', label: 'Estoque e inventário', icon: Package, view: StockPage },
  { id: 'cash', label: 'Caixa', icon: Wallet, view: CashPage },
  { id: 'expenses', label: 'Despesas', icon: Receipt, view: ExpensesPage },
  { id: 'weekly', label: 'Relatório semanal', icon: ClipboardCheck, view: WeeklyReportPage },
];
const fromHash = (): Page => nav.find(n => `#${n.id}` === location.hash)?.id ?? 'overview';

export default function App() {
  const [page, setPage] = useState<Page>(fromHash);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { const listener = () => setPage(fromHash()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener); }, []);
  function navigate(next: Page) { location.hash = next; setPage(next); setMenuOpen(false); window.scrollTo({ top: 0 }); }
  const current = nav.find(n => n.id === page)!;
  return <div className="app-shell">
    {menuOpen && <button className="sidebar-overlay" onClick={() => setMenuOpen(false)} aria-label="Fechar menu" />}
    <aside id="menu" className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
      <div className="brand"><span className="brand-symbol"><Store size={22} /></span><span>Cantina em Dia<small>SENAI · Paulista</small></span></div>
      <nav aria-label="Navegação principal">{nav.map(item => <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} aria-current={page === item.id ? 'page' : undefined} onClick={() => navigate(item.id)}><item.icon size={18} />{item.label}</button>)}</nav>
    </aside>
    <div className="main-shell">
      <header className="topbar no-print"><button className="icon-button mobile-menu" aria-label="Abrir menu" aria-controls="menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Menu size={21} /></button><strong>{current.label}</strong></header>
      <main><current.view navigate={navigate} /></main>
    </div>
  </div>;
}
