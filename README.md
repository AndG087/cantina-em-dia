# Cantina em Dia

Sistema local para acompanhar a cantina do Senai em Paulista. Ele cobre só as cinco atividades pedidas pela gestão:

| Atividade | Tela | O que o sistema faz |
|---|---|---|
| **Calendário da escola**: cursos em andamento, feriados e paralisações | Calendário da escola | Cursos e turmas por turno, com alunos aproximados; feriados, recessos e paralisações com o efeito na cantina; registro de cada averiguação com a escola (vence em 7 dias). Dia com "cantina fechada" não exige caixa. Sábado e domingo podem abrir com um evento de "Funcionamento solicitado". |
| **Compras**: comprar, conferir notas e quantidades, fazer o inventário | Compras e notas · Estoque e inventário | Pedido ao fornecedor e recebimento com o valor da nota (obrigatório). Se a nota não bate com os itens, exige explicação. Aponta custo 10% acima do estimado e itens que faltam chegar. A folha de inventário conta vários itens de uma vez. |
| **Caixa**: conferir todo dia aberturas e fechamentos | Caixa | Abertura com troco e fechamento com vendas em dinheiro, Pix, cartão e voucher, retiradas e dinheiro contado. Aponta dia sem abertura, troco diferente do fechamento anterior, diferença de contagem e caixa sem fechar. Também alerta para abertura após 07h30 e fechamento antes das 22h nos dias úteis de funcionamento. Você registra a conferência de cada dia. |
| **Gestão**: relatório semanal | Relatório semanal | Semana comparada à anterior, com caixa, compras, estoque, gastos, calendário e pendências. Imprime ou salva em PDF, copia o texto para o WhatsApp, baixa em .md e guarda a versão entregue. |
| **Despesas**: identificar gastos fora do padrão | Despesas | Aponta despesa 50% acima do usual da categoria, possível lançamento duplicado, categoria 30% acima da média e compra 15% mais cara que as anteriores do item. Você registra a explicação de cada alerta. |

A tela **Rotina da gestão** mostra se cada atividade está em dia, precisa de atenção ou está pendente.

Uma descrição completa das funcionalidades, para leitura e impressão, está em `docs/Funcionalidades_Cantina_em_Dia.docx`.

Valores são conferências a partir do que foi lançado: um alerta ou diferença pede verificação, não prova erro ou desvio. O sistema não consulta o Senai, a maquininha nem o banco.

## Instalar e iniciar (Windows)

Requisitos: Windows x64, Python 3.12+ (comando `python`), Node.js 22.12+ e MySQL 8 ou mais novo rodando neste computador (serviço do Windows, porta 3306).

```powershell
cd C:\dev\cantina-em-dia
npm.cmd run setup   # só na primeira vez: pede a senha do root do MySQL
npm.cmd start
```

Na primeira vez, o `setup` cria no MySQL os bancos `cantina_em_dia` e `cantina_em_dia_test` e o usuário `cantina`, com senha aleatória e acesso só a esses bancos, e grava a conexão no `.env`. A senha do root não é guardada. Para refazer só essa parte: `.venv\Scripts\python.exe backend\setup_mysql.py`.

Abra http://127.0.0.1:5173 e mantenha o terminal aberto; **Ctrl+C** encerra o sistema (o MySQL continua ligado como serviço). O sistema só atende neste computador.

## Dados e cópias de segurança

- Os dados ficam no MySQL local, banco `cantina_em_dia` (dá para consultar pelo MySQL Workbench). A senha do usuário `cantina` fica no `.env`, que não vai para o Git.
- A cada dia, o primeiro `npm.cmd start` cria uma cópia em `%LOCALAPPDATA%\CantinaEmDia\backups` (`cantina-AAAAMMDD-HHMMSS.json.gz`). Copie esses arquivos para um pendrive ou nuvem de vez em quando. Para desativar: `CANTINA_AUTO_BACKUP=0` no `.env`.
- Restaurar: num banco vazio já com a estrutura criada (o `npm.cmd start` cria a estrutura), rode dentro de `backend`:

```powershell
..\.venv\Scripts\python.exe -m app.backup restore "C:\caminho\cantina-AAAAMMDD-HHMMSS.json.gz"
```

A restauração só aceita banco vazio e cópia da mesma versão da estrutura (atualmente `0002_vale_refeicao`). Cópias anteriores à migração exigem um banco com a estrutura daquela versão.


## Validar

```powershell
npm.cmd run build   # TypeScript e Vite
npm.cmd test        # testes no banco separado cantina_em_dia_test
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
backend/setup_mysql.py  prepara bancos e usuário no MySQL
scripts/             instalação, inicialização e testes
```

Versões anteriores, com vendas por item, equipe, produção, preços, metas, importação e anexos, estão no histórico do Git (até o commit `f8e8838`). Até o commit `34a5e3b` o sistema usava PostgreSQL.

## Cadastro inicial da cantina

O banco local recebeu 217 itens das listas de feira, bomboniere e salgados em 10/11/2026. Os saldos e mínimos começam em zero: use **Estoque e inventário** para conferir as unidades e registrar a contagem real. A quantidade da lista de compras não foi tratada como estoque disponível.

Os arquivos locais `contratos/cadastrar_itens.py` e `contratos/Catalogo_inicial_referencia.csv` ficam fora do Git junto aos documentos de origem. O script pode ser executado novamente com `.venv\Scripts\python.exe contratos\cadastrar_itens.py`, com a API na porta 8000: preserva os itens já existentes. O CSV documenta os custos de referência disponíveis para 37 itens, sem criar compras ou despesas. No sistema, custos entram pelo recebimento das notas. Produtos embalados sem peso definido usam unidade de embalagem; confira isso antes da primeira movimentação.

## Protótipo da interface (isolado)

Com o frontend ligado por `npm.cmd start`, abra http://127.0.0.1:5173/proposta?cenario=rotina#home. A aplicação atual continua em `/`. Para ver o primeiro uso: http://127.0.0.1:5173/proposta?cenario=primeiro-uso#home.

Essa rota usa somente dados fictícios no navegador e não consulta a API. As etapas e os registros aparecem no endereço; rascunhos e exemplos ficam separados por cenário. “Reiniciar exemplo” limpa somente o cenário escolhido. A análise e os limites estão em `docs/proposta-interface/revisao-react.md`.
