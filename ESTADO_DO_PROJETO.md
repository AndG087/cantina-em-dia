# Estado do projeto

Atualizado em 10 de novembro de 2026. Repositório: `C:\dev\cantina-em-dia`. Versão local 0.5.0. Commits feitos localmente; não houve envio ao GitHub.

## Continuidade autorizada

O usuário pediu “continue”. A pausa anterior foi encerrada e o desenvolvimento foi retomado, mantendo um commit por etapa validada. Anexos (8b) e backup/restauração (8c) estão concluídos. Os módulos das etapas 1 a 8 estão disponíveis; a próxima frente é validar o fluxo com as informações reais e resolver as regras de negócio ainda abertas.

## Entregas registradas

| Etapa | Commit | Entrega |
|---|---|---|
| 1 | abb0ec1 | React, FastAPI, PostgreSQL, documentos e configurações |
| 2 | 9965ab1 | Equipe, escalas, substituições, feriados, confirmações e auditoria |
| 3 | 3c7f4ae | Estoque, lotes, validade, movimentos, estornos e inventário |
| 4 | ff98dda | Pedidos, aprovação, recebimento parcial e reembolsos |
| 5 | 893d222 | Caixa, vendas, despesas, conciliação, cancelamentos e devoluções |
| 6 | 1761cf1 | Receitas versionadas, produção, rendimento e porções |
| 7 | dd69a20 | Painel, relatórios mensais, metas e apurações preservadas |
| 8a | 3e69f6e | CSV com mapeamento, prévia, validação e rastreabilidade |
| 8b | e1aa190 | Anexos com integridade e arquivamento reversível |
| 8c | 703f43d | Backup consistente, importação e restauração em banco isolado |
| 9 | (este commit) | Rotina de acompanhamento: calendário da escola, notas, inventário em folha, caixa diário, gastos fora do padrão e relatório semanal |

## Importação concluída

- CSV UTF-8 ou Windows-1252, até 2 MB e 2.000 linhas.
- Tipos: cadastro, resumo financeiro, venda por produto, recebimento digital e saldo inicial por lote.
- Seleção de colunas com campos obrigatórios e modelos de cabeçalho.
- Prévia sem gravação de lançamentos; validação repetida ao confirmar.
- Uma transação para todo o lote, com rollback em erro.
- Proteção por hash do arquivo e referências externas únicas.
- Conteúdo original preservado no banco, com download como texto.
- Resumos sem itens não baixam estoque nem inventam custo; a apuração sobre resultado permanece pendente nesses casos.

## Verificações finais desta etapa

- 58 testes passaram em PostgreSQL isolado (`cantina_em_dia_test`).
- Build TypeScript/Vite passou.
- `alembic check` passou: nenhuma alteração de estrutura pendente em relação aos modelos.
- Inicializador criou o primeiro backup local dos dados existentes. Pela interface, o teste restaurou essa cópia em outro banco, comparou os registros e removeu o banco temporário; a data de verificação apareceu no histórico.
- Telas de backup e anexos conferidas no navegador; console sem avisos/erros nessa conferência. Nenhum cadastro ou comprovante fictício foi inserido no banco operacional.
- A porta 8000 já estava ocupada por outra instância. Para a conferência, foram usadas temporariamente 8011/5184, sem alterar o `.env` nem encerrar processos alheios.
- Há um aviso de depreciação da biblioteca de testes Starlette/httpx, sem falha nos testes.

## Executar

```powershell
cd C:\dev\cantina-em-dia
npm.cmd start
```

Interface padrão: `http://127.0.0.1:5173`. Migrações são aplicadas pelo inicializador. Em instalação nova, executar `npm.cmd run setup` primeiro. Portas podem ser configuradas no `.env` quando necessário.

## O que ainda está pendente

- Validação do fluxo de anexos com comprovantes reais recebidos da equipe. O recebimento manual, vínculo, download e arquivamento reversível já estão disponíveis.
- Definir onde guardar a cópia externa dos backups e executar a rotina com os dados reais. A criação, verificação e restauração já estão disponíveis; não há envio automático para nuvem.
- Integração automática com Stone/WhatsApp. O que existe é lançamento manual e importação CSV assistida.
- Adaptação e validação com o arquivo real exportado pela solução Stone contratada.
- Confirmação dos nomes/horários da equipe, cardápio, tabela oficial de preços, regras de consumo e base/valor da meta.
- Revisão com dados reais dos custos e regras antes do uso operacional definitivo. Retificação gerencial por lote e vigências de preço estão implementadas; retificações financeiras de notas, compras já liquidadas e pagamentos ainda exigem fluxo adicional.
- Acesso remoto e autenticação não fazem parte do escopo atual: em 9 de novembro o usuário confirmou que somente ele acessará o sistema e que manterá o uso local em loopback.

## Dados e segurança do repositório

Credenciais estão em `.env`, ignorado pelo Git. Dados ativos do PostgreSQL em `%LOCALAPPDATA%\CantinaEmDia\postgres`, fora do OneDrive. Não tratar cópia de arquivos de um banco ativo como backup consistente. Dados de testes são isolados do banco operacional.

## Anexos (8b)

Quatro testes adicionais verificam integridade e download, rejeição de formatos inválidos, vínculo e arquivamento reversível e proteção de caminhos/referências. Testes usam armazenamento temporário isolado. Build TypeScript/Vite aprovado.

## Backup e recuperação (8c)

- ZIP lógico próprio da aplicação com registros de todas as tabelas e anexos, inclusive arquivados. Não inclui credenciais, código ou outros ZIPs de backup.
- Snapshot em transação PostgreSQL REPEATABLE READ, valores decimais preservados, datas com fuso e sequências restauradas sem reutilizar IDs reservados.
- Verificação de hash, tamanho, estrutura, revisão de migração e arquivos vinculados. Não executa SQL do arquivo nem extrai caminhos arbitrários.
- Teste de restauração em banco temporário, conferência dos registros e remoção ao concluir. Falha de limpeza é informada sem marcar sucesso.
- Recuperação cria um banco novo com nome gerado; não sobrescreve o banco em uso. Recupera anexos ausentes e preserva arquivos locais diferentes. A troca do banco no `.env` é manual.
- Importação de ZIP externo para recuperar o catálogo; verificação e restauração disponíveis também por CLI.
- Cópia automática na primeira inicialização do dia pelo `npm.cmd start`; pode ser desativada com `CANTINA_AUTO_BACKUP=0`. Não é um serviço contínuo ou agendado.
- Armazenamento em `%LOCALAPPDATA%\CantinaEmDia\backups`, configurável com `CANTINA_DATA_DIR`. O diretório do PostgreSQL permanece separado.
- Migração daquela entrega: `0010_backups`; estrutura atual: `0013_lot_lookup_index`. Este formato exige a mesma revisão para recuperar; guardar o código correspondente junto à estratégia de cópia externa. Procedimento completo no README.

Nove testes adicionais cobrem restauração real com decimais, datas, horários, JSON e sequências; recuperação física de anexo ausente; preservação do banco de origem; arquivos adulterados; perda do catálogo; duplicidade; limites; caminhos indevidos; revisão incompatível; proteção do banco original; criação diária pelo CLI e bloqueio de alterações iniciadas por outro site. Os dados, arquivos e bancos de recuperação dos testes são isolados e limpos.

## Preços com vigência

Etapa adicional autorizada em 9 de novembro. Nova tela Preços e custos, com origem, motivo, vigência e cancelamento de regras sem vendas posteriores. A venda manual e o CSV por item conferem o preço fixado na data da ocorrência. Uma regra não pode alcançar vendas já registradas. O cadastro inicial foi preservado pela migração 0011_price_rules. Alterações de preço devem usar o novo fluxo. Validação: 50 testes passaram e o build TypeScript/Vite passou. A retificação gerencial foi concluída na etapa seguinte, com histórico e prévia de impacto.

## Retificação gerencial de custos

Correção por lote com documento, motivo, confirmação e prévia. Os registros originais e as apurações guardadas não são alterados. Uma camada de avaliação aplica a revisão aos relatórios, lotes, vendas e produções relacionadas, inclusive custos antes desconhecidos e lotes sem saldo. Novos movimentos usam o custo corrigido. Não altera nota, despesa, pagamento, quantidade ou custo padrão do cadastro. Uma prévia desatualizada é rejeitada. O histórico permite outra revisão para corrigir uma correção. Apurações antigas recebem aviso de revisão posterior. Documentos podem ser vinculados às regras de preço e às correções. Corrigido também o cálculo de perdas manuais estornadas no relatório. Validação desta entrega: 58 testes em PostgreSQL isolado e build TypeScript/Vite aprovados. Migração 0012_cost_revisions, versão 0.4.0.

## Consulta de custos por lote

Após a retificação, a consulta usada em novos movimentos foi ajustada para buscar apenas os lotes movimentados e suas origens. Isso evita carregar todo o histórico a cada venda. Índice por lote na migração 0013_lot_lookup_index. Os relatórios continuam avaliando os registros necessários para os custos históricos corrigidos. O teste de propagação para vendas futuras permanece na suíte.

## Guia de administração e mapa das funcionalidades

Documentos adicionados em 9 de novembro de 2026:

- GUIA_PRATICO_DA_CANTINA.md: guia para iniciante com implantação, primeiros trinta dias, rotina remota de duas a três horas à tarde, modelos de mensagens, caixa físico, Pix/cartão, estoque, compras, reembolsos, marmitas, preços, equipe, cuidados com alimentos e fechamento mensal. Exemplos são fictícios e não foram cadastrados no banco. Referências oficiais do Sebrae e Anvisa no próprio guia.
- MAPA_FUNCIONALIDADES.md: entradas, resultados, regras, exemplos, conexões, correções e limites de todos os módulos, com atalhos internos.

Ambos estão na área Documentos, com leitura, download Markdown e botão de impressão/salvar PDF pelo navegador. Suporte a tabelas e listas de conferência por remark-gfm. Atualizado o teste da lista permitida de documentos. Navegador: leitura de ambos, tabela, checklists e atalho para Preços e custos conferidos; console sem avisos/erros nessa sessão. A captura de imagem não ficou disponível na ferramenta nesta sessão, portanto não foi usada como evidência visual.

Verificação final: 58 testes passaram, build TypeScript/Vite aprovado, alembic check sem diferenças. PostgreSQL operacional atualizado para 0013_lot_lookup_index. Novo backup dessa revisão criado e restauração verificada em banco temporário, removido ao concluir. A conferência usou portas temporárias 8011/5184 e não encerrou a instância preexistente em 8000/5173.

Pendências para implantação: dados reais da equipe/cardápio/custos/estoque, tabela oficial, regras de consumo, acordo da meta, arquivo real da Stone, destino externo do backup e conferência acompanhada de um ciclo operacional. Retificação financeira de compras liquidadas/pagamentos continua sem fluxo completo; a retificação entregue é de custo gerencial por lote. Acesso remoto e autenticação seguem fora do escopo confirmado pelo usuário. Nada foi enviado ao GitHub.

## Rotina de acompanhamento (etapa 9)

Em 10 de novembro de 2026 o usuário trouxe as atividades que precisa entregar para a cantina do Senai: calendário da escola (cursos em andamento, feriados e paralisações), compras (comprar, conferir notas e quantidades, inventário), caixa (conferir diariamente fechamentos e aberturas), gestão (relatório semanal) e despesas (gastos fora do padrão). O que já existia foi mantido; foram acrescentados:

- **Calendário da escola** (`school.py`, tela Calendário da escola): cursos/turmas com turno, dias, período e alunos; feriados, recessos, férias, paralisações e eventos com efeito previsto; cancelamento com motivo; registro de averiguação (vence em 7 dias). Eventos com efeito "cantina fechada" passam a fechar o dia para o responsável previsto e para a conferência do caixa.
- **Conferência de notas** (`purchases.py`): valor total da nota no recebimento, com explicação obrigatória quando difere da soma dos itens; consulta `/api/purchase-receipts` com nota × itens, custo × estimado (10%) e pedidos com itens a receber. A despesa continua sendo a soma dos itens.
- **Folha de inventário** (`inventory.py`, Estoque): saldo esperado por item no horário de corte e gravação de vários itens em uma única transação, reaproveitando a regra da contagem individual.
- **Conferência diária do caixa** (`cash_review.py`, Caixa): por dia, aberturas, fechamentos, passagens, vendas em dinheiro, retiradas e apontamentos (dia útil sem abertura, troco diferente do fechamento anterior, diferenças, caixa sem fechamento, caixa em dia fechado). Conferência registrada com ou sem ressalvas; fica "desatualizada" se os registros do dia mudarem (impressão digital dos dados).
- **Gastos fora do padrão** (`expense_alerts.py`, Financeiro): mediana da categoria (+50%, mínimo 3 lançamentos em 180 dias), duplicidade (mesmo favorecido e valor em 7 dias), categoria acima da média de períodos anteriores (+30% e R$ 50; somente despesas manuais), custo de compra +15% sobre as últimas compras do item e categoria nova (informativo). Explicação registrada por alerta.
- **Relatório semanal** (`weekly.py`, tela Relatório semanal): semana de segunda a domingo comparada à anterior, com caixa, compras, estoque, gastos e calendário; Markdown imprimível, texto para WhatsApp, download `.md` e versões guardadas com retrato dos números. O cálculo mensal foi separado em `period_report` sem mudar o resultado do mês.
- **Rotina da gestão** na Visão geral (`/api/routine`): situação das cinco atividades com atalho para cada tela.
- Migração `0014_rotina_acompanhamento` (novas tabelas e dois campos em `purchase_receipts`); versão 0.5.0.

### Verificações desta etapa

- 65 testes passaram em PostgreSQL isolado (7 novos em `test_routine.py`).
- Build TypeScript/Vite aprovado.
- `alembic check` sem diferenças; downgrade e upgrade da 0014 testados no banco de testes.
- Conferência no navegador em uma instância separada (portas 8011/5184) com banco temporário `cantina_preview_demo` e dados fictícios; o banco foi apagado ao final. Telas conferidas: Visão geral, Calendário da escola, Caixa (incluindo o bloqueio de "sem ressalvas" com apontamentos), Compras, Financeiro, Relatório semanal (inclusive a versão impressa) e folha de inventário. Sem rolagem horizontal em 390 px.
- O banco operacional **não** foi alterado nesta etapa: a migração 0014 será aplicada pelo `npm.cmd start` na próxima inicialização. Faça um backup antes, como de costume.

### Pendências desta etapa

- Cadastrar o calendário real (cursos, turnos, alunos, feriados e paralisações) a partir da averiguação com a escola.
- Os critérios de "fora do padrão" e os prazos (7 dias para calendário e inventário) são fixos; ajustar depois de algumas semanas com dados reais, se gerarem alertas demais ou de menos.
- Com pouco histórico, as comparações de despesas ficam limitadas; a tela informa as categorias sem histórico suficiente.
- Diferença entre nota e itens não altera a despesa; frete, desconto e ajustes financeiros de nota continuam sem fluxo próprio.
