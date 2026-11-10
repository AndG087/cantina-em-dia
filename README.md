# Cantina em Dia

Sistema local para acompanhar a cantina do Senai em Paulista. Ele cobre só as cinco atividades pedidas pela gestão:

| Atividade | Tela | O que o sistema faz |
|---|---|---|
| **Calendário da escola**: cursos em andamento, feriados e paralisações | Calendário da escola | Cursos e turmas por turno, com alunos aproximados; feriados, recessos e paralisações com o efeito na cantina; registro de cada averiguação com a escola (vence em 7 dias). Dia com "cantina fechada" não exige caixa. |
| **Compras**: comprar, conferir notas e quantidades, fazer o inventário | Compras e notas · Estoque e inventário | Pedido ao fornecedor e recebimento com o valor da nota (obrigatório). Se a nota não bate com os itens, exige explicação. Aponta custo 10% acima do estimado e itens que faltam chegar. A folha de inventário conta vários itens de uma vez. |
| **Caixa**: conferir todo dia aberturas e fechamentos | Caixa | Abertura com troco e fechamento com vendas em dinheiro, Pix e cartão, retiradas e dinheiro contado. Aponta dia sem abertura, troco diferente do fechamento anterior, diferença de contagem e caixa sem fechar. Você registra a conferência de cada dia. |
| **Gestão**: relatório semanal | Relatório semanal | Semana comparada à anterior, com caixa, compras, estoque, gastos, calendário e pendências. Imprime ou salva em PDF, copia o texto para o WhatsApp, baixa em .md e guarda a versão entregue. |
| **Despesas**: identificar gastos fora do padrão | Despesas | Aponta despesa 50% acima do usual da categoria, possível lançamento duplicado, categoria 30% acima da média e compra 15% mais cara que as anteriores do item. Você registra a explicação de cada alerta. |

A tela **Rotina da gestão** mostra se cada atividade está em dia, precisa de atenção ou está pendente.

Valores são conferências a partir do que foi lançado: um alerta ou diferença pede verificação, não prova erro ou desvio. O sistema não consulta o Senai, a maquininha nem o banco.

## Instalar e iniciar (Windows)

Requisitos: Windows x64, Python 3.12+ (comando `python`) e Node.js 22.12+. O PostgreSQL vem junto (pacote `@embedded-postgres`); não precisa de Docker.

```powershell
cd C:\dev\cantina-em-dia
npm.cmd run setup   # só na primeira vez
npm.cmd start
```

Abra http://127.0.0.1:5173 e mantenha o terminal aberto; **Ctrl+C** encerra tudo. O sistema só atende neste computador.

## Dados e cópias de segurança

- O banco fica em `%LOCALAPPDATA%\CantinaEmDia\postgres`, fora do OneDrive. A senha gerada fica no `.env` (não versionado); guarde esse arquivo.
- A cada dia, o primeiro `npm.cmd start` cria uma cópia em `%LOCALAPPDATA%\CantinaEmDia\backups` (`cantina-AAAAMMDD-HHMMSS.json.gz`). Copie esses arquivos para um pendrive ou nuvem de vez em quando. Para desativar: `CANTINA_AUTO_BACKUP=0` no `.env`.
- Restaurar: com o PostgreSQL ligado (`node scripts/database.mjs` em um terminal), em outro terminal crie um banco vazio, aplique as migrações e rode, dentro de `backend`:

```powershell
..\.venv\Scripts\python.exe -m app.backup restore "C:\caminho\cantina-AAAAMMDD-HHMMSS.json.gz"
```

A restauração só aceita banco vazio e cópia da mesma versão da estrutura (`0001_inicial`).

Para usar um PostgreSQL já instalado, copie `.env.example` para `.env`, ajuste `DATABASE_URL` e use `CANTINA_MANAGED_POSTGRES=0`.

## Validar

```powershell
npm.cmd run build   # TypeScript e Vite
npm.cmd test        # testes em um banco separado, cantina_em_dia_test
```

## Organização

```text
backend/app/
  school.py      calendário da escola
  purchases.py   pedidos, recebimento com nota e conferência
  stock.py       itens, movimentos e inventário
  cash.py        abertura, fechamento e conferência diária do caixa
  expenses.py    despesas e gastos fora do padrão
  weekly.py      relatório semanal e rotina da gestão
  backup.py      cópia de segurança e restauração
backend/migrations/  estrutura do banco
backend/tests/       um arquivo de testes por atividade
frontend/src/pages/  uma tela por atividade
scripts/             instalação, inicialização e testes
```

Versões anteriores, com vendas por item, equipe, produção, preços, metas, importação e anexos, estão no histórico do Git (até o commit `f8e8838`).
