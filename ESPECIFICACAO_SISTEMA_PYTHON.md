# Sistema local de gestão da cantina em Python

Especificação inicial de 7 de novembro de 2026. Requisitos em levantamento. A fundação foi implementada em `C:\dev\cantina-em-dia`: React, FastAPI, PostgreSQL, migração inicial e configurações. Os módulos operacionais abaixo continuam planejados. Consulte `ESTADO_DO_PROJETO.md` para o estado atualizado.

## 1. Uso esperado

O gerente usará o próprio computador para administrar estoque e dinheiro da cantina do Senai em Paulista. Pretende dedicar duas a três horas por dia, com visitas à tarde, sem presença pela manhã e sem trabalho à noite. As despesas são de responsabilidade dos pais e da cantina.

O sistema precisa apoiar esse modelo de trabalho. Informação que depende de contagem física, recebimento ou fechamento deve ser produzida por alguém no local e disponibilizada ao gerente para revisão posterior.

## 2. Armazenamento e arquitetura propostos

- Aplicação em Python para uso no computador do gerente.
- Banco de dados PostgreSQL local, conforme escolha posterior do usuário. Essa escolha substitui a proposta inicial de SQLite.
- Histórico de alterações e cópias de segurança datadas, com procedimento de restauração.
- Manter os arquivos ativos do PostgreSQL fora da sincronização do OneDrive. Arquivos de backup consistentes poderão ser arquivados conforme a política definida pelo gerente.
- Datas e horários da operação em America/Sao_Paulo.
- Separação entre data da ocorrência, data do registro e responsável pelo lançamento.
- Entrada inicial proposta: Dona Gel envia mensagens privadas pelo WhatsApp do próprio celular e o gerente faz o lançamento no sistema. Preferência por texto, áudio e fotos ainda a esclarecer. A interface será em React, acessada localmente pelo navegador.

Estas escolhas são propostas técnicas, não funcionalidades já disponíveis. Não há integração confirmada com a Stone. Os formatos de exportação e recursos do sistema contratado precisam ser verificados antes de definir importação ou integração automática.

## 3. Responsável pelo caixa: escala e confirmação

Requisito explícito: indicar automaticamente quem está designado para o caixa conforme dia e horário, com possibilidade de controle manual.

Manter dois campos distintos:

- **Responsável previsto:** calculado a partir da escala vigente, calendário de funcionamento e exceções cadastradas.
- **Responsável confirmado:** pessoa que assumiu o caixa, mediante registro de abertura ou passagem de responsabilidade.

Exibir também início do turno, último registro recebido e pendências. Sem confirmação, apresentar “previsto, sem confirmação”. A passagem do horário da escala não comprova presença nem transfere automaticamente a responsabilidade pelo dinheiro contado.

Regras propostas:

1. Cadastrar funcionários, escalas semanais e datas de vigência.
2. Cadastrar feriados, férias, dias fechados e alterações pontuais de horário.
3. Permitir substituição temporária por data e intervalo, exigindo motivo e autor da alteração. Uma substituição pontual tem prioridade sobre a escala semanal.
4. Tratar ausência de escala como “sem responsável definido”. Em dia fechado, mostrar “cantina fechada”. Escalas conflitantes geram pendência de definição.
5. Permitir confirmação manual e troca com horário efetivo, pessoa que entrega, pessoa que recebe e contagem do caixa. Guardar os valores esperado, contado e a diferença na passagem.
6. Registrar mudanças sem apagar o histórico. Uma edição posterior da escala não deve reatribuir vendas e fechamentos antigos.
7. Uma mesma pessoa pode ter atribuição de cozinha e referência local, mas só deve constar como responsável pelo caixa quando designada para essa função.
8. A indicação por horário deve atualizar enquanto a aplicação estiver aberta e ao retomá-la após suspensão. O método de recebimento das confirmações locais ainda será definido.

O pedido de acompanhamento em tempo real envolve duas situações: a escala pode ser calculada localmente pelo relógio; dados reais da cantina exigem envio de informações. Exibir a data da última atualização, inclusive quando estiver atrasada. A arquitetura local não dá, por si só, acesso aos acontecimentos da cantina.

## 4. Controles previstos

| Área | Requisito |
|---|---|
| Painel | Responsável previsto e confirmado, última atualização, fechamentos pendentes, itens prioritários e resumo financeiro do período |
| Estoque | Cadastro de itens e unidades, saldo inicial, entradas, consumo, perdas, contagens e ajustes justificados |
| Compras | Lista solicitada por Dona Gel, aprovação, fornecedor, quantidade pedida, recebida e pendente, custo e documento |
| Compras e reembolsos | Dona Gel guarda a nota e informa a compra; o pai costuma reembolsar por Pix. Vincular compra, recebimento e reembolso para evitar duplicidade |
| Produtos em falta | Registrar item, data, período de indisponibilidade e previsão de reposição. A rotina informada é comprar no dia seguinte, sem compra emergencial habitual |
| Produtos e preços | Cardápio e preços, com identificação dos valores fixados pela licitação, fonte e vigência |
| Produção | Ficha técnica, rendimento medido, marmitas de tamanho fixo, refeições da equipe, sobras e perdas |
| Caixa | Abertura, passagem, recebimentos em espécie, despesas, retiradas, fechamento e diferença |
| Recebimentos digitais | Vendas e recebimentos separados, taxas e conciliação dos registros disponíveis da Stone |
| Despesas | Categoria, documento, vencimento, pagamento, origem do recurso e responsável |
| Equipe | Funções, escala, substituições e responsáveis pelos registros |
| Meta | Base e valor pendentes, apuração somente depois da definição do acordo, histórico por período |
| Relatórios | Fechamento diário, compras, inventário, movimentações e resultado mensal |

## 5. Fluxo de trabalho proposto

1. Dona Gel envia informações pelo WhatsApp privado e guarda comprovantes. O gerente lança os dados no sistema local e identifica a data da ocorrência e a data de lançamento. Definir quem cobre os demais turnos e ausências.
2. O fechamento noturno é feito pelo responsável no local e fica disponível para a próxima janela de administração do gerente. Dona Gel é a única candidata conhecida atualmente; confirmar se permanece até o encerramento antes de atribuir a tarefa.
3. Na janela à tarde, o gerente revisa o fechamento anterior, confere recebimentos digitais e despesas, atualiza estoque e acompanha compras e pendências.
4. Visitas à tarde atendem à entrega de mercadorias, conferências físicas, implantação e treinamento, com frequência a definir.
5. Dona Gel continua como referência para reposição, com responsabilidades compatíveis com sua carga de cozinha. Definir quem cobre sua ausência.

Não inventar vendas ou saldos para preencher dias sem registros. Valores desconhecidos e fechamentos não enviados devem aparecer como pendências.

## 6. Informações necessárias para a implementação

- Relação de funcionários, funções, dias, horários e trocas de caixa.
- Quem confirma a abertura, passagem e fechamento. Confirmar os horários de Dona Gel e seu substituto.
- Forma das mensagens pelo WhatsApp e recursos da equipe para fotos, contagens e identificação de datas e turnos.
- Nome do aplicativo e pacote Stone, acesso a relatórios e exemplo de exportação sem dados sensíveis desnecessários.
- Definição de caixa por turno ou compartilhado, rotina de guarda e recolhimento de espécie.
- Produtos, unidades, inventário inicial e preços fixados pela licitação.
- Identificação dos documentos de compras e dos Pix de reembolso, incluindo valores ainda pendentes.
- Regras de refeições da equipe, cortesias, retiradas e fiado.
- Base, valor, período e condições da meta.

## 7. Ordem proposta de implementação

1. Cadastro da equipe, escala e indicação automática do responsável previsto, com confirmação e substituição manual.
2. Abertura, passagem, fechamento, retiradas e pendências do caixa.
3. Cadastro e movimentação de estoque, lista de compras e recebimento.
4. Despesas e relatórios de acompanhamento.
5. Importação de dados da Stone conforme formato validado e conciliação sem duplicidade.
6. Produção, custos e meta após levantamento das receitas e do acordo.

Antes de usar na operação, testar conflitos e exceções da escala, início e fim dos horários, troca de responsável, falta de confirmação, dados atrasados, dinheiro transferido para banco, compras com reembolso e restauração de backup. Os testes devem verificar os controles de gestão, além da interface.

## 8. Recebimento de informações pelo WhatsApp

Fluxo inicial proposto para manter a rotina familiar de Dona Gel: receber mensagem, registrar no sistema, vincular o comprovante quando houver e marcar o que foi conferido. O gerente poderá cadastrar informações recebidas com atraso, preservando a data original do acontecimento. Uma foto ou mensagem recebida ainda não equivale a lançamento conferido.

No cadastro, guardar remetente, data da ocorrência, data do lançamento, tipo de informação, valores ou quantidades, anexo quando disponível e situação: pendente de informação, lançado ou conferido. Contagens sem data de corte, unidade ou responsável devem gerar pendência.

Fechamento sugerido, sujeito à disponibilidade da equipe: data e turno, pessoa que contou, troco inicial, dinheiro contado no final, despesas ou retiradas em espécie, comprovantes e observações. Separar a lista de faltas e perdas do registro financeiro. O sistema calcula o caixa esperado a partir dos registros disponíveis; não inventa o valor das vendas em dinheiro quando essa informação falta.

Para compras reembolsadas, registrar o documento, itens e quantidades, total, quem adiantou o dinheiro e os pagamentos de reembolso vinculados. Manter o saldo a reembolsar e o comprovante de Pix. Nota reenviada ou comprovante do mesmo pagamento deve ser sinalizado para revisão, evitando duplicar a compra ou sua liquidação.

Não há conexão automática com o WhatsApp nesta proposta inicial. O acompanhamento financeiro e o estoque serão atualizados após os lançamentos do gerente; a indicação do responsável previsto continua sendo calculada pela escala. A tela deve mostrar essa diferença e a data da última informação recebida.
