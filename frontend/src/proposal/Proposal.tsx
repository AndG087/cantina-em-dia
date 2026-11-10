import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ChartColumn, Ellipsis, ShoppingBasket, Sun, Wallet } from 'lucide-react';
import type { DemoState, Scenario } from './data';
import { loadState, resetState, storeState } from './data';
import { Heading, Link, Notice } from './components';
import Dashboard from './Dashboard';
import DailyFlow from './DailyFlow';
import Today from './Today';
import CashBook from './CashBook';
import PurchaseFlow from './PurchaseFlow';
import StockFlow from './StockFlow';
import { Catalog, DayDetail, Expense, History, More, Purchases, ReceiptDetail, School, Summary } from './Views';
import '@fontsource/barlow/400.css';
import '@fontsource/barlow/600.css';
import '@fontsource/barlow/700.css';
import '@fontsource/barlow-condensed/600.css';
import '@fontsource/barlow-condensed/700.css';
import './styles.css';

const tabs = [{ id: 'inicio', label: 'Início', Icon: ChartColumn }, { id: 'home', label: 'Hoje', Icon: Sun }, { id: 'cash', label: 'Caixa', Icon: Wallet }, { id: 'purchases', label: 'Compras', Icon: ShoppingBasket }, { id: 'more', label: 'Mais', Icon: Ellipsis }];
const scenarioFromURL = (): Scenario => new URLSearchParams(location.search).get('cenario') === 'primeiro-uso' ? 'primeiro-uso' : 'rotina';
const routeFromURL = () => location.hash.slice(1) || 'inicio';
export default function Proposal() {
  const scenario = scenarioFromURL();
  const [route, setRoute] = useState(routeFromURL);
  const [state, setState] = useState<DemoState>(() => loadState(scenario));
  const [storageFailed, setStorageFailed] = useState(false);
  const [resetConfirm, setResetConfirm] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { const handle = () => { setRoute(routeFromURL()); setResetConfirm(false); }; window.addEventListener('hashchange', handle); return () => window.removeEventListener('hashchange', handle); }, []);
  useLayoutEffect(() => {
    window.scrollTo(0, 0);
    ref.current?.querySelector<HTMLHeadingElement>('[data-page-title]')?.focus({ preventScroll: true });
    document.title = `${ref.current?.querySelector('h1')?.textContent || 'Proposta'} · Cantina em Dia`;
  }, [route]);
  const update = (next: DemoState) => { setState(next); setStorageFailed(!storeState(scenario, next)); };
  const parts = route.split('/'), view = parts[0];
  const props = { state, scenario, update, parts };
  const group = ['daily', 'cash', 'day', 'expense', 'history'].includes(view) ? 'cash' : ['buy', 'purchases', 'receipt', 'stock'].includes(view) ? 'purchases' : view === 'home' || view === 'inicio' ? view : 'more';
  let content;
  switch (view) {
    case 'inicio': content = <Dashboard key={route} state={state} parts={parts} />; break;
    case 'home': content = <Today state={state} />; break;
    case 'cash': content = <CashBook state={state} parts={parts} />; break;
    case 'daily': content = <DailyFlow state={state} scenario={scenario} update={update} segment={parts[1] || 'start'} />; break;
    case 'day': content = <DayDetail key={route} {...props} />; break;
    case 'buy': content = <PurchaseFlow state={state} scenario={scenario} update={update} />; break;
    case 'purchases': content = <Purchases {...props} />; break;
    case 'receipt': content = <ReceiptDetail {...props} />; break;
    case 'stock': content = <StockFlow state={state} update={update} />; break;
    case 'expense': content = <Expense {...props} />; break;
    case 'summary': content = <Summary key={route} {...props} />; break;
    case 'history': content = <History {...props} />; break;
    case 'school': content = <School {...props} />; break;
    case 'catalog': content = <Catalog {...props} />; break;
    case 'more': content = <More {...props} />; break;
    default: content = <><Heading title="Tela não encontrada" /><Link to="inicio">Ir para o Início</Link></>;
  }
  return <div className="p-app" ref={ref}>
    <a className="p-skip" href="#p-content" onClick={e => { e.preventDefault(); document.getElementById('p-content')?.focus(); }}>Pular para o conteúdo</a>
    <div className="p-review-bar"><span><strong>Protótipo</strong> com dados fictícios. Nada aqui altera o sistema.</span><div className="p-review-controls"><label htmlFor="scenario">Cenário</label><select id="scenario" value={scenario} onChange={e => { location.href = `/proposta?cenario=${e.target.value}#home`; }}><option value="rotina">Rotina em andamento</option><option value="primeiro-uso">Primeiro uso</option></select><button className="p-link" onClick={() => setResetConfirm(true)}>Reiniciar exemplo</button><a className="p-link" href="/">Sistema atual</a></div></div>
    <header className="p-masthead"><div><span className="p-brand"><span className="p-brand-symbol" aria-hidden="true"><svg viewBox="0 0 40 40" width="40" height="40"><circle cx="20" cy="21" r="7" fill="currentColor" /><g stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M20 5v5M7.5 10.5l3.5 3.5M32.5 10.5 29 14M4 21h5M31 21h5" /></g><path d="M5 31c4-3 8 3 12 0s8 3 12 0 6 1 7 0" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg></span><span>Cantina em Dia<small>SENAI Paulista</small></span></span><nav aria-label="Navegação da proposta">{tabs.map(({ id, label, Icon }) => <a key={id} href={`#${id}`} aria-current={group === id ? 'page' : undefined}><Icon size={22} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span></a>)}</nav></div></header>
    <main id="p-content" tabIndex={-1}>
      {storageFailed && <Notice danger>O navegador não permitiu guardar os exemplos. As mudanças serão mantidas somente enquanto a página estiver aberta.</Notice>}
      {resetConfirm && <Notice><p>Reiniciar somente os dados fictícios e rascunhos deste cenário?</p><div className="p-actions"><button className="p-button p-secondary" onClick={() => setResetConfirm(false)}>Cancelar</button><button className="p-button p-primary" onClick={() => { setState(resetState(scenario)); try { localStorage.removeItem(`cantina.proposta.v4.compra.${scenario}`); } catch { /* Simulador local. */ } location.href = `/proposta?cenario=${scenario}#home`; location.reload(); }}>Reiniciar cenário</button></div></Notice>}
      {content}
      <footer className="p-footer">Simulação para revisar a interface. Nenhuma operação chama a API ou altera o banco real.</footer>
    </main>
  </div>;
}
