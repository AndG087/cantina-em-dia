# Mapa das funcionalidades do Cantina em Dia

Versão 0.5.0 · 10 de novembro de 2026 · Uso pessoal no computador do gerente

Este mapa explica o que cada área faz, quais informações você precisa reunir e como os registros se conectam. Use-o como índice do sistema. Os links dos módulos abaixo abrem a área correspondente quando você estiver lendo dentro da aplicação.

Você será o único operador do sistema. A equipe envia informações e comprovantes; você confere e registra. Não há acesso externo, login ou coleta automática do que acontece na cantina.

## 1 A ordem dos registros

**Equipe e escala → cadastro e estoque inicial → compras e recebimento → produção → vendas → recebimentos e pagamentos → conferência de caixa e estoque → relatório e meta → backup.**

Algumas atividades acontecem em paralelo. O importante é registrar cada fato uma vez, com a data da ocorrência, o responsável quando previsto e os documentos disponíveis.

| Aconteceu na cantina | Primeiro registro | Registro posterior ou conferência |
|---|---|---|
| Chegou mercadoria de um pedido | Recebimento em Compras | Conferência do lote e pagamento da despesa vinculada |
| Dona Gel comprou com dinheiro próprio | Compra/recebimento com adiantamento da funcionária | Reembolso vinculado à mesma despesa |
| Foram preparadas marmitas | Produção com ingredientes e rendimento | Venda ou consumo/perda do produto pronto |
| Cliente pagou no cartão | Venda e forma de pagamento | Crédito efetivo e taxa em Financeiro |
| Houve troca de pessoa no caixa | Passagem com contagem em Caixa | Comparação entre esperado, contado e diferença |
| Foi identificado custo antigo errado | Prévia em Preços e custos | Correção confirmada e nova conferência do relatório |
| Recebeu uma foto de nota | Anexo recebido, se ainda não há lançamento | Vínculo à compra, despesa ou outro registro |

## 1.1 Rotina exigida pela gestão

Cinco atividades precisam ser acompanhadas. A **Visão geral** mostra a situação de cada uma e abre a tela correspondente.

| Atividade | Tela | Frequência sugerida | Considerada em dia quando |
|---|---|---|---|
| Calendário da escola: cursos em andamento, feriados e paralisações | [Calendário da escola](#school) | Semanal | Houve averiguação registrada nos últimos 7 dias |
| Compras: comprar, conferir notas e quantidades, fazer inventário | [Compras](#purchases) e [Estoque](#inventory) | A cada recebimento; contagem semanal | Notas dos últimos 7 dias sem divergência e contagem física nos últimos 7 dias |
| Caixa: conferir fechamentos e aberturas | [Caixa](#cash) | Diária | Os últimos 7 dias estão conferidos ou não tinham movimento previsto |
| Gestão: preparar relatório semanal | [Relatório semanal](#weekly) | Semanal | A semana anterior tem uma versão guardada |
| Despesas: identificar gastos fora do padrão | [Financeiro](#finance) | Semanal | Nenhum alerta sem explicação nos últimos 30 dias |

"Em dia" significa que os registros foram feitos e conferidos no sistema. Não substitui a conferência física, os documentos ou a conversa com a equipe.

## 2 Visão geral

[Abrir Visão geral](#overview)

**Serve para:** começar a conferência do dia e localizar pendências. Mostra indicadores do mês, responsável previsto e confirmado, caixas abertos, estoque prioritário, lotes vencidos e despesas pendentes.

**Você precisa:** ter registrado os fatos nos outros módulos. O painel é um resumo desses registros.

**Exemplo:** um produto aparece abaixo do mínimo; você confere o saldo físico e decide incluí-lo no próximo pedido.

**Limite:** a última atualização do aplicativo não comprova que a equipe já enviou todos os dados do dia. Também não há previsão automática de demanda.

## 3 Equipe e escala

[Abrir Equipe e escala](#team)

**Você pode:** cadastrar e atualizar funcionários; definir escalas semanais e vigências; registrar substituições por data e intervalo; cadastrar dias fechados; confirmar quem assumiu a responsabilidade; consultar ocorrências de auditoria.

**Entradas:** nomes, funções, dias, horários, datas de vigência, exceções e justificativas.

**Saídas:** responsável previsto pelo calendário, responsável confirmado, conflitos e histórico. A indicação é atualizada periodicamente com a aplicação aberta.

**Regra central:** a escala representa a designação. A confirmação representa um registro de quem assumiu; ela também pode ser produzida na abertura ou passagem de caixa. Uma pessoa de confiança não é automaticamente responsável por todos os horários.

**Limite:** não é folha de pagamento, ponto eletrônico nem comprovação automática de presença. Como somente você acessará, deverá registrar as confirmações a partir das informações recebidas.

## 3.1 Calendário da escola

[Abrir Calendário da escola](#school)

**Você pode:** cadastrar cursos e turmas com turno, dias de aula, início, término e número aproximado de alunos; registrar feriados, recessos, férias, paralisações e eventos com o efeito previsto na cantina (fechada, movimento reduzido, sem alteração ou movimento maior); cancelar registros com motivo; registrar cada averiguação com a escola.

**Saídas:** calendário de dias úteis com situação, turmas por turno e alunos estimados; cursos que começam ou terminam nas próximas duas semanas; histórico de averiguações.

**Regras centrais:** um evento com efeito **cantina fechada** funciona como dia fechado: o sistema não espera abertura de caixa nem responsável naquele dia. A averiguação é considerada vencida depois de 7 dias. Alterações de curso exigem motivo e ficam no histórico.

**Limite:** o sistema não consulta o Senai. As informações dependem do que você averiguar com a secretaria ou coordenação. O número de alunos é uma estimativa para planejar compras e produção.

## 4 Estoque e inventário

[Abrir Estoque](#inventory)

**Você pode:** cadastrar produtos, ingredientes e embalagens; definir unidade e mínimo; registrar entradas e saldo inicial por lote; indicar validade; lançar consumo, perda, consumo da equipe, cortesia e devolução ao fornecedor; registrar contagem física com ajuste justificado; estornar movimentos manuais permitidos.

**Entradas:** SKU, nome, categoria, tipo, unidade, quantidade, custo conhecido ou pendente, data/hora, lote, validade e motivo.

**Saídas:** saldo por item, lotes com saldo, movimentos e divergências entre quantidade esperada e contada.

**Regras centrais:** saldo negativo é bloqueado; itens em un exigem quantidades inteiras; o sistema verifica disponibilidade do lote na data da ocorrência e impede certas alterações depois de movimentar o item. Lotes vencidos são bloqueados para venda e preparo. Entradas e saídas passadas são verificadas contra o histórico disponível.

**Folha de inventário:** escolha o grupo (todos, produtos, ingredientes ou embalagens) e o horário de corte, carregue a folha com o saldo esperado de cada item e preencha só o que foi contado. A diferença aparece enquanto você digita. Todos os itens preenchidos são gravados juntos; se o saldo de algum mudou desde que a folha foi carregada, nada é gravado e a tela pede para recarregar.

**Como corrigir:** movimentos ligados a venda, compra ou produção devem ser tratados pela operação de origem, respeitando os bloqueios existentes. A contagem física corrige quantidade. A correção de custo é feita em Preços e custos; são tarefas diferentes.

**Limite:** não há balança conectada nem contagem automática. Cadastro de validade não acompanha temperatura ou conservação física. O mínimo é informado por você.

## 5 Compras e reembolsos

[Abrir Compras e reembolsos](#purchases)

**Você pode:** cadastrar fornecedores, criar pedidos, aprovar pedidos, receber total ou parcialmente e indicar quem pagou. A chegada da mercadoria gera estoque por lote e uma despesa vinculada ao recebimento.

**Entradas:** fornecedor, solicitante, itens, quantidades pedidas e recebidas, custo unitário, nota/documento, data, lote, validade e quem adiantou o recurso.

**Saídas:** pedido solicitado/aprovado/parcial/recebido, itens pendentes e despesa correspondente.

**Regras centrais:** é necessário aprovar antes de receber; não se pode receber quantidade acima do pedido; documentos repetidos do mesmo fornecedor são rejeitados. O pagamento/reembolso liquida a despesa vinculada.

**Conferência das notas:** no recebimento, informe o valor total impresso na nota. Se for diferente da soma dos itens, o sistema exige a explicação (desconto, frete, item faltante) ou a correção das quantidades e custos. A tabela de conferência mostra, para cada nota, os itens recebidos, o custo comparado ao estimado no pedido (alerta a partir de 10% acima), a diferença da nota e a situação: conferida, com divergência ou sem valor da nota. A lista de pedidos em aberto mostra o que ainda falta receber. A despesa continua sendo a soma dos itens; a diferença da nota fica registrada para conferência.

**Exemplo:** Dona Gel recebeu uma compra de R$ 80 paga do bolso dela. Você informa o adiantamento; quando seu pai reembolsa, lança o pagamento na mesma despesa, com a referência do Pix.

**Limite:** correções do valor financeiro de um recebimento já gravado, devoluções com crédito de fornecedor e alteração de pagamentos não têm um fluxo completo de notas de ajuste. Não use uma correção de custo gerencial para fingir que o documento ou o pagamento foi corrigido. Registre a pendência e confira com seus pais.

## 6 Produção e marmitas

[Abrir Produção e marmitas](#production)

**Você pode:** cadastrar fichas técnicas versionadas, ingredientes e embalagens, rendimento previsto, quantidade realmente produzida, consumo medido ou estimado, lote e validade do produto pronto; definir padrões por componente e registrar amostras de porções.

**Entradas:** produto de saída, receita, quantidades, data, instruções, rendimento e pesagens.

**Saídas:** ingredientes consumidos, produto pronto em estoque, custo da produção e desvios das amostras em relação à tolerância definida.

**Regras centrais:** a produção baixa ingredientes e gera produto pronto. A venda baixa somente o produto pronto. Alterações de receita são novas versões. Dados estimados permanecem identificados. A correção de um lote de ingrediente repercute no custo gerencial das produções e vendas relacionadas.

**Como corrigir:** o cancelamento de produção tem bloqueios de estoque e deve ser usado quando a reversão física e os registros forem possíveis. Ele não desfaz automaticamente vendas já ocorridas. Não crie um lote negativo para forçar o cancelamento.

**Limite:** o sistema não mede os alimentos, não valida segurança sanitária e não transforma uma divergência de porção em prova de desvio.

## 7 Vendas

[Abrir Vendas](#sales)

**Você pode:** registrar produtos, quantidades e preços; aplicar desconto permitido; dividir pagamento entre dinheiro, Pix, débito e crédito; registrar referência externa; cancelar venda, indicar devolução física e registrar devolução efetiva do dinheiro.

**Entradas:** data/hora da venda, itens, quantidade, preço unitário, desconto, pagamentos e caixa quando necessário.

**Saídas:** venda, baixa do produto pronto, custo associado e pagamentos a receber ou devolver.

**Regras centrais:** pagamentos devem somar o total; não pode vender sem estoque disponível; preços fixados seguem a vigência da data da ocorrência; descontos não podem reduzir os itens fixados pela licitação. Venda em dinheiro exige caixa aberto e horário compatível.

**Como corrigir:** cancelar e registrar a devolução são ações distintas. Marque devolução ao estoque apenas quando o produto realmente retornou em condição adequada. A segurança do alimento precisa ser avaliada pela operação.

**Limite:** não é um emissor fiscal e não recebe automaticamente vendas da Stone. Para venda antiga, confira o preço daquela data; a sugestão do cadastro é o preço vigente na consulta.

## 8 Caixa

[Abrir Caixa](#cash)

**Você pode:** abrir o caixa com troco contado, registrar reforço e retirada, passar a responsabilidade com contagem, fechar e reabrir o último caixa quando permitido para correção.

**Entradas:** pessoa, data/hora, troco inicial, valores contados, destino/motivo de retiradas e justificativas.

**Saídas:** dinheiro esperado, dinheiro contado, diferença e histórico de movimentos e passagens. Vendas, despesas e devoluções em espécie geram movimentos vinculados.

**Regras centrais:** apenas um caixa aberto; o dinheiro não pode ficar negativo nos registros; horários precisam respeitar abertura e passagens; a reabertura é restrita ao último caixa encerrado. Diferenças contadas em uma passagem não devem ser somadas duas vezes no fechamento.

**Conferência diária:** a tabela dos últimos 14 dias mostra, por dia, aberturas, fechamentos, vendas em dinheiro, retiradas e pontos de atenção: dia de funcionamento sem abertura, troco de abertura diferente do valor contado no fechamento anterior, diferença na passagem ou no fechamento, caixa que ficou aberto e caixa aberto em dia previsto como fechado. Registre a conferência do dia como **sem ressalvas** ou **com ressalvas**, com o encaminhamento. Um dia com pontos de atenção não pode ser marcado sem ressalvas. Se os registros do dia mudarem depois, a conferência aparece como desatualizada.

**Boa prática:** registre retiradas e depósitos **antes** da contagem de fechamento. Assim o valor contado é o troco que fica, e a abertura do dia seguinte deve ter o mesmo valor.

**Limite:** o aplicativo não conta a gaveta. Uma retirada não é automaticamente despesa ou perda: registre o motivo e o destino para conferir com seu pai.

## 9 Financeiro

[Abrir Financeiro](#finance)

**Você pode:** registrar despesas manuais, vencimento, documento, favorecido, finalidade e quem adiantou; registrar pagamentos parciais ou totais, recurso da cantina ou do proprietário; conciliar créditos digitais com valor bruto, taxa, data e referência.

**Entradas:** despesa e pagamento, ou o pagamento da venda ao qual o recebimento se refere.

**Saídas:** despesas não pagas, reembolsos pendentes, créditos digitais a conciliar e histórico dos valores registrados.

**Regras centrais:** pagamento não pode exceder o saldo da despesa; referências repetidas são bloqueadas; taxa não pode superar o crédito bruto; recebimento não pode exceder o pagamento da venda. Despesa manual ainda não paga pode ser cancelada conforme as regras. Despesas de mercadorias preservam o vínculo com a compra.

**Gastos fora do padrão:** o painel no topo do Financeiro compara os gastos do período escolhido (padrão: últimos 30 dias) com o histórico registrado:

- despesa manual 50% ou mais acima da mediana da mesma categoria, com pelo menos 3 lançamentos nos últimos 180 dias;
- possível duplicidade: mesmo favorecido e mesmo valor em até 7 dias;
- despesas manuais de uma categoria 30% acima da média dos períodos anteriores de mesma duração, com pelo menos R$ 50 de diferença;
- custo por unidade de uma compra 15% ou mais acima da média das últimas compras do mesmo item;
- primeira despesa em uma categoria (informativo).

Registre a explicação de cada alerta. Ela aparece no relatório semanal e tira o alerta da lista de pendências. Um alerta é um ponto de conferência, não prova de erro ou desvio.

**Limite:** não há conexão bancária, cálculo tributário, folha de pagamento ou transferência real de dinheiro. Você registra fatos; o sistema não realiza pagamentos.

## 10 Preços e custos

[Abrir Preços e custos](#adjustments)

### Vigências de preço

Cadastre produto, preço, data/hora de início, indicação de preço fixado, documento e motivo. Uma tabela futura pode ser registrada antes da data. A regra inicial permanece no histórico. Uma nova regra não pode alcançar vendas já registradas do produto, e o cancelamento também é bloqueado nessa situação.

Use **Comprovantes e anexos** com o vínculo **Vigência de preço** e o ID da regra para guardar a autorização. O campo textual de documento não substitui o arquivo.

### Retificação do custo gerencial

Escolha um lote de entrada, informe o custo por unidade de controle, confirme o documento e gere a prévia. O sistema informa vendas e produções afetadas. Confirme somente depois de conferir. Se o estoque ou os custos mudaram desde a prévia, é necessário gerar outra.

O custo original é preservado. As revisões ficam no histórico; os relatórios e consultas usam o custo gerencial corrigido. Lotes já consumidos também podem ser corrigidos. Lotes produzidos na cantina são recalculados a partir dos ingredientes e embalagens e não recebem uma alteração direta de custo.

Uma correção posterior pode alterar o resultado consultado de meses antigos. Apurações guardadas permanecem com seu retrato anterior e recebem um aviso de que há revisão posterior de custos. Confira novamente antes de combinar qualquer diferença na sua remuneração.

Para corrigir uma correção, registre outra revisão com motivo e documento. Use o vínculo **Correção de custo** em anexos. A operação não altera notas, despesas, pagamentos, preços de venda nem quantidades. O custo padrão do cadastro, usado para novas entradas sem custo explícito, é separado do custo do lote corrigido.

## 11 Relatórios e meta

[Abrir Relatórios e meta](#reports)

**Você pode:** escolher o mês, consultar vendas, descontos, cancelamentos, custos, perdas e consumo registrado, despesas, taxas, recebimentos, fluxo de caixa, estoque valorizado, diferenças de caixa, série diária e produtos de maior venda. É possível baixar um CSV com os indicadores disponíveis.

**Meta:** há bases distintas para vendas brutas, vendas após descontos/cancelamentos, recebimentos líquidos e resultado gerencial. Registre o acordo e o valor confirmado. Uma mudança gera uma nova versão da meta.

**Apuração:** guarde uma simulação ou uma conferência aprovada para mês encerrado. O retrato dos indicadores usado na apuração é preservado. A parcela variável representa o excedente positivo da base escolhida; não é um cálculo de folha salarial.

**Regras centrais:** custos desconhecidos, vendas importadas sem itens, produção estimada e conciliação incompleta podem impedir a apuração sobre resultado. Mercadorias compradas não são novamente descontadas como despesa operacional quando seu custo já é reconhecido por consumo/venda.

**Limite:** “sem pendências identificadas” não garante que todo fato foi informado. Impostos, contas e outras obrigações precisam estar corretamente registrados e conferidos. O sistema não define seu acordo com seus pais.

## 11.1 Relatório semanal

[Abrir Relatório semanal](#weekly)

**Você pode:** escolher qualquer dia da semana desejada (padrão: a semana anterior), ler o relatório, imprimir ou salvar em PDF, copiar um resumo pronto para WhatsApp, baixar em Markdown e guardar a versão entregue com uma observação (para quem, como e quando).

**Conteúdo:** vendas, recebimentos, despesas, perdas, diferenças de caixa, pedidos, ticket médio e resultado registrado comparados à semana anterior; formas de pagamento; tabela da conferência diária do caixa com os pontos de atenção; notas recebidas e divergências; pedidos em aberto; contagens físicas e diferenças; itens abaixo do mínimo e lotes vencendo; gastos fora do padrão com as explicações; calendário da escola da semana e das duas seguintes; lista de pendências.

**Regras centrais:** uma semana vai de segunda a domingo. Uma semana em andamento é identificada como tal. Cada versão guardada preserva o retrato dos números naquele momento e recebe um número de versão; uma nova entrega da mesma semana cria a versão seguinte.

**Limite:** o relatório resume os registros lançados. Dias sem informação aparecem como pendência, não como zero confiável.

## 12 Importação CSV

[Abrir Importação CSV](#imports)

**Tipos disponíveis:** cadastro de produtos/insumos; resumo financeiro de vendas; vendas por produto; recebimentos digitais; saldo inicial por lote.

**Como usar:** escolha o tipo, arquivo, codificação e colunas; valide a prévia; confira erros e exemplos; só então confirme. Aceita UTF-8 ou Windows-1252, até 2 MB e 2.000 linhas. Há modelos de cabeçalhos.

**Regras centrais:** a prévia não grava lançamentos; o lote é revalidado e confirmado em uma transação; arquivos e referências externas já importados são rejeitados. Vendas por produto usam o mesmo fluxo de venda e conferência de preço. O arquivo original fica preservado no histórico.

**Limite:** um resumo sem produtos não baixa estoque nem inventa custo e deixa o resultado incompleto. O modelo de vendas por produto precisa de adaptação para relatórios com vários itens por pedido. O formato real da solução Stone ainda precisa ser validado. Não há sincronização automática.

## 13 Comprovantes e anexos

[Abrir Comprovantes e anexos](#attachments)

**Você pode:** enviar arquivo para a caixa de recebidos, vincular ou relincar com justificativa, baixar, visualizar imagens e arquivar/recuperar sem apagar o original.

**Vínculos:** despesa, pagamento/reembolso, venda, pedido de compra, movimento de estoque, contagem física, produção, caixa, funcionário/treinamento, vigência de preço e correção de custo.

**Formatos:** PDF, PNG, JPEG, WebP, texto UTF-8 e áudios compatíveis MP3, M4A, OGG/Opus e WAV; até 8 MB por arquivo. O conteúdo é conferido contra o formato. O download verifica tamanho e hash, e duplicatas ativas no mesmo vínculo são rejeitadas.

**Limite:** não há leitura do WhatsApp, reconhecimento automático da nota ou lançamento por áudio. Você precisa salvar e anexar o arquivo, ler/conferir o conteúdo e registrar o fato financeiro ou de estoque.

## 14 Backup e recuperação

[Abrir Backup e recuperação](#backups)

**Você pode:** criar uma cópia ZIP, baixá-la, importar uma cópia externa, testar a restauração e criar um banco restaurado separado. Os registros e anexos, inclusive arquivados, são incluídos. Há acesso por linha de comando para recuperação.

**Automático:** o inicializador tenta criar uma cópia local na primeira inicialização de cada dia com `npm.cmd start`. Não é uma tarefa executada continuamente nem funciona com o computador desligado.

**Teste:** cria outro banco, restaura e compara os registros, verifica arquivos e remove o banco temporário ao concluir. Uma falha não é marcada como verificação concluída.

**Recuperação:** cria uma cópia em outro banco e recupera anexos ausentes. O banco em uso permanece disponível. A troca de configuração é manual e está descrita no README e na tela.

**Limites:** o formato exige a mesma revisão de estrutura do aplicativo; preserve o código correspondente. A versão 0.5.0 usa `0014_rotina_acompanhamento`. Cópias anteriores exigem o código e a revisão correspondentes para recuperar, antes de atualizar novamente. O ZIP não inclui senha, programas ou outros ZIPs e não é criptografado. Os limites de tamanho estão no README. Não há cópia automática externa ou para nuvem.

## 15 Documentos configurações e plano

[Abrir Documentos](#documents) · [Abrir Configurações](#settings) · [Abrir Plano de implantação](#roadmap)

**Documentos:** reúne o projeto de gestão, especificação, perguntas para seu pai, prompt de desenvolvimento, guia prático e este mapa. Permite ler e baixar os arquivos. O guia e o mapa descrevem o uso atual; o planejamento contém propostas e regras ainda em levantamento.

**Configurações:** nome da cantina, localização e nome do gerente, persistidos no PostgreSQL. A meta é definida no módulo de relatórios. Caminhos locais e portas são configurações técnicas no `.env`.

**Plano:** apresenta os módulos entregues. A disponibilidade técnica não substitui cadastro e validação dos dados reais.

## 16 Histórico armazenamento e conferência

Alterações importantes registram eventos de auditoria com motivo quando exigido. O histórico pode ser consultado na área de equipe e também compõe o banco e os backups. A autoria padrão é de gerente local; não há assinatura digital nem autenticação individual de quem enviou uma mensagem.

O PostgreSQL e os arquivos anexados ficam fora do repositório. Credenciais ficam no `.env`, ignorado pelo Git. O sistema atende em loopback, para uso pessoal neste computador. Sua cópia externa deve incluir o ZIP e uma estratégia separada para preservar código e configurações.

Muitas listas exibem somente os últimos 500 registros; itens, lotes e regras têm limites próprios, geralmente 2.000. Uma lista parcial não é um extrato completo. Relatórios mensais consultam os registros do período no banco e não ficam limitados às linhas visíveis nessas listas.

## 17 O que continua dependendo de informações reais

- Equipe, escalas, cardápio, receitas, custos, estoque inicial e regras de consumo.
- Documento e vigências da tabela oficial de preços.
- Base e valor da meta, aprovação e pagamento pelos seus pais.
- Arquivo real exportado pela solução Stone e extrato de taxas e créditos.
- Conferência acompanhada de um ciclo de operação, com dinheiro e mercadoria físicos.
- Local escolhido para guardar o backup externo e rotina de conferência da cópia.

Continua fora desta versão: integração automática Stone/WhatsApp, acesso remoto, emissão fiscal, contabilidade, folha de pagamento, controle sanitário completo, automação de câmeras, previsão de demanda e fluxo completo de retificação financeira de compras já liquidadas.

## 18 Roteiro para aprender o sistema

1. Leia o Guia prático e combine responsabilidades e dados de partida.
2. Cadastre a equipe e poucos produtos prioritários com informações reais.
3. Confira uma contagem inicial e um recebimento acompanhado.
4. Registre uma produção e veja as duas mudanças de estoque: ingredientes e produto pronto.
5. Acompanhe uma venda, o recebimento e o fechamento do caixa.
6. Compare o relatório com os documentos e teste um backup.
7. Amplie os cadastros e a rotina conforme conseguir manter a conferência.

Para experimentar com dados fictícios, use uma instalação/banco separado. O banco operacional deve conter apenas fatos reais e as correções documentadas.
