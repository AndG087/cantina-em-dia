import { useEffect, useState } from 'react';
import type { FormEvent, ComponentType } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowDownLeft, ArrowUpRight, Check,
  CheckCircle2, ChevronLeft, ChevronRight, ClipboardList,
  Clock3, Database, Download, FileText, LayoutDashboard, Leaf, Loader2,
  MapPin, Menu, Package, RefreshCw, Settings2, ShieldCheck, Store,
  Target, Users, Wallet, X,
} from 'lucide-react';
import { api } from './api';
import TeamPage from './pages/TeamPage';
import InventoryPage from './pages/InventoryPage';
import PurchasesPage from './pages/PurchasesPage';
import CashPage from './pages/CashPage';
import SalesPage from './pages/SalesPage';
import FinancePage from './pages/FinancePage';
import ProductionPage from './pages/ProductionPage';
import ReportsPage from './pages/ReportsPage';
import Dashboard from './pages/Dashboard';
import ImportsPage from './pages/ImportsPage';
import AttachmentsPage from './pages/AttachmentsPage';
import BackupsPage from './pages/BackupsPage';
import AdjustmentsPage from './pages/AdjustmentsPage';
import type { AppSettings, DatabaseHealth, DocumentInfo } from './api';

type Page = 'overview' | 'roadmap' | 'documents' | 'settings' | 'team' | 'inventory' | 'purchases' | 'cash' | 'sales' | 'finance' | 'production' | 'reports' | 'imports' | 'attachments' | 'backups' | 'adjustments';
type Icon = ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
const nav: { id: Page; label: string; icon: Icon }[] = [
  { id: 'overview', label: 'Visão geral', icon: LayoutDashboard },
  { id: 'sales', label: 'Vendas', icon: Store },
  { id: 'cash', label: 'Caixa', icon: Wallet },
  { id: 'finance', label: 'Financeiro', icon: ArrowDownLeft },
  { id: 'purchases', label: 'Compras e reembolsos', icon: ClipboardList },
  { id: 'production', label: 'Produção e marmitas', icon: Leaf },
  { id: 'inventory', label: 'Estoque', icon: Package },
  { id: 'adjustments', label: 'Preços e custos', icon: Settings2 },
  { id: 'team', label: 'Equipe e escala', icon: Users },
  { id: 'reports', label: 'Relatórios e meta', icon: Target },
  { id: 'imports', label: 'Importação CSV', icon: Download },
  { id: 'attachments', label: 'Comprovantes e anexos', icon: FileText },
  { id: 'backups', label: 'Backup e recuperação', icon: ShieldCheck },
  { id: 'roadmap', label: 'Plano de implantação', icon: ClipboardList },
  { id: 'documents', label: 'Documentos', icon: FileText },
  { id: 'settings', label: 'Configurações', icon: Settings2 },
];
const phases = [
  ['Fundação do sistema', 'Interface, API, banco de dados e documentos reunidos.', 'Disponível'],
  ['Equipe e responsáveis pelo caixa', 'Escalas, confirmação de abertura e substituições manuais.', 'Disponível'],
  ['Estoque e inventário inicial', 'Produtos, unidades e movimentações com histórico.', 'Disponível'],
  ['Compras e reembolsos', 'Solicitações da Dona Gel, recebimento e pagamentos.', 'Disponível'],
  ['Caixa e financeiro', 'Vendas, despesas, passagens e fechamento por turno.', 'Disponível'],
  ['Produção e marmitas', 'Receitas, rendimento, porções, sobras e perdas.', 'Disponível'],
  ['Relatórios e meta', 'Resultados do mês e remuneração conforme o acordo.', 'Disponível'],
  ['Importações e continuidade', 'CSV, comprovantes, backup e recuperação com conferência.', 'Disponível'],
];
export default function App() {
  const [page, setPage] = useState<Page>(() => {
    const candidate = location.hash.replace('#', '');
    return nav.some(n => n.id === candidate) ? candidate as Page : 'overview';
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [health, setHealth] = useState<DatabaseHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [document, setDocument] = useState<{ id: string; title: string; content: string } | null>(null);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [toast, setToast] = useState('');

  function navigate(next: Page) { setPage(next); setMenuOpen(false); setDocument(null); location.hash = next; }

  async function refresh() {
    setLoading(true); setError('');
    const results = await Promise.allSettled([
      api<{ status: string }>('/health'), api<DatabaseHealth>('/health/database'),
      api<AppSettings>('/settings'), api<DocumentInfo[]>('/documents'),
    ]);
    const database = results[1];
    setHealth(database.status === 'fulfilled' ? database.value : null);
    const configuration = results[2];
    if (configuration.status === 'fulfilled') setSettings(configuration.value);
    else setSettings(null);
    if (results[3].status === 'fulfilled') setDocs(results[3].value);
    const failure = results.find(r => r.status === 'rejected');
    if (failure?.status === 'rejected') setError(failure.reason instanceof Error ? failure.reason.message : 'Não foi possível atualizar as informações.');
    setLoading(false);
  }

  useEffect(() => { void refresh(); const timer = setInterval(() => { void refresh(); }, 60000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    const listener = () => {
      const next = location.hash.slice(1);
      if (nav.some(n => n.id === next)) { setPage(next as Page); setDocument(null); }
    };
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 4500); return () => clearTimeout(timer); }, [toast]);

  async function openDocument(id: string) {
    navigate('documents'); setDocumentLoading(true);
    try {
      const result = await api<{ title: string; content: string }>(`/documents/${id}`);
      setDocument({ id, ...result });
    } catch (e) { setToast(e instanceof Error ? e.message : 'Não foi possível abrir o documento.'); }
    finally { setDocumentLoading(false); }
  }

  const currentPage = nav.find(n => n.id === page)!;
  return <div className="app-shell">
    {menuOpen && <button className="sidebar-overlay" onClick={() => setMenuOpen(false)} aria-label="Fechar menu" />}
    <aside id="main-navigation" className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
      <a className="brand" href="#overview" onClick={() => navigate('overview')} aria-label="Cantina em Dia, início">
        <span className="brand-symbol"><Store size={25} strokeWidth={1.6} /></span>
        <span>Cantina<span className="brand-second">em Dia<span className="brand-dot">.</span></span></span>
      </a>
      <div className="workspace"><span className="workspace-icon"><MapPin size={17} /></span><div><strong>{settings?.business_name || 'Cantina em Dia'}</strong><span>{settings?.location || 'SENAI · Paulista'}</span></div></div>
      <span className="nav-label">ESPAÇO DE GESTÃO</span>
      <nav aria-label="Navegação principal">{nav.map(item => <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)} aria-current={page === item.id ? 'page' : undefined}><item.icon size={19} strokeWidth={1.7} />{item.label}{page === item.id && <span className="nav-dot" />}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-note"><ShieldCheck size={20} /><div><strong>No seu computador</strong><span>Armazenamento local</span></div></div><div className="profile"><span className="avatar">{settings?.manager_name?.slice(0, 1).toUpperCase() || 'G'}</span><div><strong>{settings?.manager_name || 'Sua gestão'}</strong><span>Administrador local</span></div><button className="icon-button profile-settings" onClick={() => navigate('settings')} aria-label="Abrir configurações"><Settings2 size={17} /></button></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" aria-label="Abrir menu" aria-controls="main-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Menu size={21} /></button><span>Meu espaço</span><ChevronRight size={13} /><strong>{currentPage.label}</strong></div><div className="topbar-right"><span className={`connection-pill ${health ? 'connected' : 'disconnected'}`}><span />{loading ? 'Verificando conexão' : health ? 'Sistema local conectado' : 'Conexão pendente'}</span><span className="topbar-avatar">{settings?.manager_name?.slice(0, 1).toUpperCase() || 'G'}</span></div></header>
      <main id="main-content">
        {error && <div className="error-banner" role="alert"><div><strong>Precisamos verificar a conexão.</strong><span>{error}</span></div><button onClick={() => void refresh()} className="button secondary small" disabled={loading}><RefreshCw size={15} />Tentar novamente</button></div>}
        {page === 'overview' && <Dashboard navigate={navigate} />}
        {page === 'roadmap' && <><PageHeading eyebrow="UM PASSO DE CADA VEZ" title="Plano de implantação" description="Cada etapa entrega uma parte funcional, antes de avançar para a próxima." /><div className="phase-intro"><CheckCircle2 size={23} /><div><strong>As oito etapas estão disponíveis</strong><p>Controles operacionais, comprovantes e recuperação dos dados implementados.</p></div><span>8 etapas</span></div><section className="phase-list">{phases.map(([title, description, status], i) => <article key={title} className={`phase-row ${i < 8 ? 'complete' : ''}`}><span className="phase-number">{i < 8 ? <Check size={20} /> : String(i + 1).padStart(2, '0')}</span><div><h2>{title}</h2><p>{description}</p></div><span className="phase-status phase-0">{status}</span></article>)}</section><div className="inline-note"><Clock3 size={18} /><p>Gestão planejada para 2–3 horas por dia, com visitas à tarde. O fechamento noturno ficará com um responsável no local.</p></div></>}
        {page === 'documents' && <><PageHeading eyebrow="CONTEXTO E PLANEJAMENTO" title={document ? document.title : 'Documentos do projeto'} description="Consulte o que já definimos e as informações que ainda precisamos reunir." />{documentLoading ? <div className="loading-box"><Loader2 className="spin" />Abrindo documento…</div> : document ? <section className="panel document-view" id="print-document"><div className="document-toolbar"><button className="text-button" onClick={() => setDocument(null)}><ChevronLeft size={17} />Todos os documentos</button><button className="button secondary small" onClick={() => window.print()}>Imprimir ou salvar PDF</button><a className="button secondary small" href={`/api/documents/${document.id}/download`}><Download size={16} />Baixar .md</a></div><article className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{document.content}</ReactMarkdown></article></section> : <section className="documents-grid">{docs.map((doc, i) => <article className="panel document-card" key={doc.id}><div className="document-card-top"><span className={`document-icon document-color-${i}`}><FileText size={26} strokeWidth={1.5} /></span><span className="file-type">MARKDOWN</span></div><h2>{doc.title}</h2><p>{doc.description}</p><div className="document-card-foot"><button className="text-button" onClick={() => void openDocument(doc.id)}>Ler documento<ArrowUpRight size={16} /></button><a className="icon-button" href={`/api/documents/${doc.id}/download`} aria-label={`Baixar ${doc.title}`}><Download size={18} /></a></div></article>)}</section>}</>}
        {page === 'backups' && <BackupsPage />}
        {page === 'attachments' && <AttachmentsPage />}
        {page === 'imports' && <ImportsPage />}
        {page === 'reports' && <ReportsPage />}
        {page === 'production' && <ProductionPage />}
        {page === 'cash' && <CashPage />}
        {page === 'sales' && <SalesPage />}
        {page === 'finance' && <FinancePage />}
        {page === 'purchases' && <PurchasesPage />}
        {page === 'inventory' && <InventoryPage />}
        {page === 'adjustments' && <AdjustmentsPage />}
        {page === 'team' && <TeamPage />}
        {page === 'settings' && <><PageHeading eyebrow="SEU ESPAÇO DE TRABALHO" title="Configurações" description="Identifique a cantina e personalize seu espaço de gestão." />{settings ? <SettingsForm settings={settings} onSaved={value => { setSettings(value); setToast('Configurações salvas no PostgreSQL.'); }} /> : <div className="panel empty-panel"><Database size={30} /><h2>Configurações indisponíveis</h2><p>Conecte o banco de dados para consultar e salvar as informações.</p><button className="button secondary" onClick={() => void refresh()}>Verificar conexão</button></div>}<div className="inline-note"><ShieldCheck size={18} /><p>Os registros ficam neste computador. A sincronização com Stone e WhatsApp será avaliada nas etapas futuras.</p></div></>}
        <footer className="page-footer"><span>Cantina em Dia <span className="footer-dot">·</span> Dados locais</span><span>Versão local <span className="footer-dot">·</span> v0.4.0</span></footer>
      </main>
    </div>
    {toast && <div className="toast" role="status"><span>{toast}</span><button className="icon-button" onClick={() => setToast('')} aria-label="Fechar aviso"><X size={17} /></button></div>}
  </div>;
}

function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div></div>;
}

function SettingsForm({ settings, onSaved }: { settings: AppSettings; onSaved: (value: AppSettings) => void }) {
  const [name, setName] = useState(settings.business_name);
  const [locationName, setLocationName] = useState(settings.location);
  const [manager, setManager] = useState(settings.manager_name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault(); setSaving(true); setError('');
    try {
      const result = await api<AppSettings>('/settings', { method: 'PUT', body: JSON.stringify({ business_name: name.trim(), location: locationName.trim(), manager_name: manager.trim(), timezone: settings.timezone }) });
      onSaved(result);
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível salvar.'); }
    finally { setSaving(false); }
  }
  return <form className="panel settings-form" onSubmit={submit}><div className="panel-heading"><div><h2>Informações da cantina</h2><p>Estas informações ficam salvas no banco local.</p></div><Store size={23} className="muted" /></div><div className="form-fields"><label>Nome da cantina<input required minLength={2} maxLength={100} value={name} onChange={e => setName(e.target.value)} /></label><label>Localização<input required minLength={2} maxLength={120} value={locationName} onChange={e => setLocationName(e.target.value)} /></label><label>Seu nome<span className="optional">Opcional</span><input maxLength={100} value={manager} onChange={e => setManager(e.target.value)} placeholder="Como você quer aparecer no sistema" /></label><label>Fuso horário<input value="Brasília — America/Sao_Paulo" readOnly className="readonly" /></label></div>{error && <p role="alert" className="form-error">{error}</p>}<div className="form-footer"><span><ShieldCheck size={15} />Salvo neste computador</span><button className="button primary" type="submit" disabled={saving}>{saving ? <Loader2 size={17} className="spin" /> : <Check size={17} />}{saving ? 'Salvando…' : 'Salvar alterações'}</button></div></form>;
}
