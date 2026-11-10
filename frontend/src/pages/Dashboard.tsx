import { ArrowUpRight, CheckCircle2, CircleDashed, TriangleAlert } from 'lucide-react';
import type { Page } from '../App';
import { Badge, ErrorNote, PageHeading, useRemote } from '../components/ui';

type Routine = { id: string; page: Page; title: string; status: 'ok' | 'attention' | 'pending'; detail: string };
const looks = { ok: { label: 'Em dia', tone: 'ok', icon: CheckCircle2 }, attention: { label: 'Atenção', tone: 'warn', icon: TriangleAlert }, pending: { label: 'Pendente', tone: 'danger', icon: CircleDashed } } as const;

export default function Dashboard({ navigate }: { navigate: (page: Page) => void }) {
  const routine = useRemote<Routine[]>('/routine');
  const done = routine.data?.filter(r => r.status === 'ok').length ?? 0;
  return <>
    <PageHeading title="Rotina da gestão" description="As cinco atividades que precisam ser acompanhadas na cantina, com a situação de cada uma." onRefresh={() => void routine.refresh()} />
    <ErrorNote errors={[routine.error]} />
    <section className="panel">
      <div className="panel-heading"><h2>Acompanhamentos</h2><span className="muted">{routine.data ? `${done} de ${routine.data.length} em dia` : 'Verificando…'}</span></div>
      <div className="routine-list">{(routine.data || []).map(item => { const look = looks[item.status]; return <button key={item.id} className={`routine-item ${look.tone}`} onClick={() => navigate(item.page)}>
        <look.icon size={20} /><div><strong>{item.title}</strong><p>{item.detail}</p></div><Badge tone={look.tone}>{look.label}</Badge><ArrowUpRight size={15} className="hide-mobile" /></button>; })}</div>
    </section>
    <div className="notice">Sugestão de ritmo: caixa todos os dias; notas a cada recebimento; contagem de estoque, gastos, calendário e relatório uma vez por semana.</div>
  </>;
}
