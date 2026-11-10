import { lazy, StrictMode, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

const Proposal = lazy(() => import('./proposal/Proposal'));
const isProposal = /^\/proposta\/?$/.test(location.pathname);

createRoot(document.getElementById('root')!).render(<StrictMode>
  {isProposal ? <Suspense fallback={<p role="status">Abrindo proposta…</p>}><Proposal /></Suspense> : <App />}
</StrictMode>);
