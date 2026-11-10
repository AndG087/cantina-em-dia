# Proposta de reorganização da interface

Proposta para discussão, em 10/11/2026. A segunda revisão está na [rota React /proposta](http://127.0.0.1:5173/proposta?cenario=rotina#home), com exemplos fictícios e sem conexão com a API. O ponto de entrada do frontend ganhou essa rota isolada; o aplicativo principal e o banco conservam seu funcionamento. O [endereço antigo](index.html) encaminha para a revisão atual.

A descrição abaixo registra a proposta de organização. Os detalhes do que já funciona no simulador, seus limites e as verificações desta revisão estão em [revisao-react.md](revisao-react.md).

## A rotina que orienta o desenho

As respostas do usuário definem o uso principal:

- Os pais recebem o resumo da equipe e registram depois, principalmente no computador.
- Precisam acompanhar recebimentos, gastos, compras, produtos e conferir as informações da equipe. Não há uma única dificuldade isolada.
- Conhecem os valores por forma de recebimento; o total de vendas deve ser calculado pelo sistema.
- O troco e o dinheiro que ficou na gaveta são informados. Os horários reais nem sempre são conhecidos. A disponibilidade do valor de retiradas não foi confirmada.
- A situação habitual de compra é comprar direto e trazer a nota, sem pedido registrado antes.

Consequência: a interface deve orientar o registro posterior do dia e da compra. “Caixa aberto agora” não deve comandar a tela inicial. Registrar uma venda por vez, calcular o total na mão ou elaborar um pedido artificial não deve fazer parte da rotina dos pais.

## O que encontrei no projeto

Foram lidas as sete páginas atuais, os componentes compartilhados e as regras de caixa, compras, estoque, escola, despesas e relatório. A análise considera a versão atual da pasta principal, com MySQL e os ajustes de VR/VA. A branch experimental de fechamento diário é outra versão e não é a base desta proposta.

| Evidência no código | Esforço ou risco para quem usa | Mudança proposta |
|---|---|---|
| `frontend/src/App.tsx`: sete destinos principais | A pessoa escolhe uma área antes de reconhecer sua tarefa | Quatro destinos: Hoje, Caixa, Compras e Mais; ações com verbos |
| Páginas: 22 entradas de formulários, geralmente recolhidas | Recolher reduz o espaço ocupado, mas a pessoa ainda precisa saber qual abrir | Abrir somente o fluxo escolhido; correções e exceções dentro do registro |
| `Dashboard.tsx`: cinco acompanhamentos com peso semelhante | Calendário, relatório e caixa disputam atenção sem considerar frequência | Registro do dia como ação principal; pendências específicas e ordenadas; rotinas semanais em segundo plano |
| `CashPage.tsx`: abrir, fechar, conferir e reabrir são formulários separados | Exige conhecer o ciclo interno do caixa e escolher o dia novamente para conferir | Um percurso “Registrar um dia”; abertura, fechamento e conferência continuam sendo etapas e registros distintos internamente |
| `CashPage.tsx`: data e hora começam no momento em que a tela abre | Registro posterior pode receber horário e dia errados | Selecionar explicitamente o dia do resumo; usar somente horários realmente informados |
| `PurchasesPage.tsx`: compra recebida exige pedido prévio; formulário de recebimento começa com linhas vazias | Na compra direta, repete produtos e cria uma etapa que não existiu na vida real | Uma tela para nota e produtos; fluxo específico de compra direta. Pedidos prévios continuam disponíveis |
| `StockPage.tsx`: 217 itens em tabela e na folha de contagem, sem busca | Obriga a percorrer todo o catálogo para encontrar poucos produtos | Busca por nome/categoria, contagem parcial e revisão dos itens preenchidos |
| `StockPage.tsx`, `weekly.py`: saldo menor ou igual ao mínimo é “Repor”, inclusive zero inicial | O primeiro uso produz centenas de sinais que não confirmam falta real | Estado “ainda não conferido”; não transformar falta de contagem em recomendação de compra |
| `StockPage.tsx`: formulário de alteração não preenche os valores ao selecionar o item | É preciso reconstruir um cadastro para alterar apenas um campo | Abrir o produto com seus valores atuais carregados; ações no contexto |
| `SchoolPage.tsx`: atualizar turma também pede preencher os campos novamente | Repete informação existente e facilita substituições incorretas | Edição preenchida a partir da turma selecionada |
| `ExpensesPage.tsx`: categoria é texto livre; há formulário separado para explicar alerta | Precisa lembrar a grafia usada e localizar de novo o alerta | Sugerir categorias existentes e registrar explicação dentro do próprio alerta |
| `ExpensesPage.tsx`: alertas aparecem antes da ação de lançar gasto | Uma tarefa simples começa pela leitura de comparações | Ação “Anotar outro gasto” direta; alertas somente quando houver algo a verificar |
| `purchases.py`: receber nota cria movimento de estoque e despesa | Compra também lançada manualmente duplica o gasto | Explicar o efeito ao salvar a compra e direcionar mercadorias para esse fluxo |
| `WeeklyReportPage.tsx`: várias formas de exportar, estatísticas e relatório completo juntos | Pede escolher formato e interpretar detalhes cedo demais | Resumo legível primeiro; copiar para WhatsApp como ação principal; PDF, arquivo e versões em opções secundárias |
| `ui.tsx`: botão genérico “Salvar” e sucesso “Registro salvo” | Não deixa claro o efeito nem a próxima ação | Botões específicos e confirmação com data, valor e situação |
| `ui.tsx` e CSS: erros de validação podem ser genéricos; textos auxiliares pequenos | Obriga a descobrir qual campo falhou e ler instruções extensas | Erro junto ao campo, preservação do que foi digitado, tipografia legível e instrução no momento da ação |

Os formulários recolhidos já são uma tentativa útil de reduzir o ruído. A proposta muda a organização por tarefas, em vez de apenas trocar cores ou deixar os mesmos formulários em cartões novos.

## O que é essencial e quando aparece

| Momento | Tarefa | Aparece imediatamente | Fica no detalhe |
|---|---|---|---|
| Ao receber o resumo | Registrar o dia e conferir o dinheiro | Dia escolhido, valores recebidos, cálculo das vendas, troco, retiradas confirmadas e gaveta | Pessoas responsáveis, observações, horários conhecidos e contexto do resumo, em seus respectivos passos |
| Ao trazer uma nota | Registrar compra e conferir o que chegou | Fornecedor, nota, produtos, quantidades, custo e total | Divergência da nota só quando existir; pedido anterior somente quando houver |
| Ao pagar outro gasto | Anotar despesa da cantina | Descrição, valor, data e categoria | Favorecido e documento continuam exigidos, mas no mesmo percurso; histórico e critérios estatísticos fora dele |
| Quando houver pendência | Conferir um registro específico | O que aconteceu, de qual dia/nota, qual a diferença e o botão para resolver | Fórmulas completas, comparação histórica e registros relacionados |
| Ao contar produtos | Ver quantidades e registrar contagem | Busca, unidade e campo de quantidade contada | Movimentos antigos e detalhes das diferenças; mínimos e unidade dentro do produto |
| Ao ocorrer perda ou ajuste | Registrar o que aconteceu | Produto, quantidade, data/hora e motivo | Listagem completa de movimentos |
| Uma vez por semana ou quando precisar | Rever valores, estoque e funcionamento | Resumo da semana e acontecimentos próximos que afetam a cantina | Relatório completo, semanas antigas, versões e comparação com períodos anteriores |
| Quando houver mudança | Registrar fechamento, evento, funcionamento solicitado ou turma | Data/período, informação e efeito na cantina | Cadastro completo de turmas, cancelamentos e confirmações antigas |

Sem vendas item a item, metas, gráficos ou novos controles de produção. A versão atual não permite calcular quantas marmitas foram vendidas a partir dos totais de dinheiro; a reformulação visual não vai alegar esse controle.

## Navegação proposta

```text
Hoje
  Registrar um dia
  Registrar uma compra / Anotar outro gasto
  Falta conferir: registros específicos, somente quando houver
  Mudança próxima de funcionamento, somente quando afetar a rotina

Caixa
  Registrar um dia
  Últimos dias → detalhes → conferir / corrigir quando permitido
  Anotar outro gasto
  Gastos e dias anteriores → filtros por período

Compras
  Registrar uma compra (padrão: compra direta com nota)
  Últimas compras → nota → produtos e conferências
  Produtos e contagem do estoque
    Buscar e contar alguns produtos
    Conferir diferenças antes de registrar
    Registrar perda/saída/entrada quando necessário
    Abrir produto → editar cadastro
  Pedidos antes da entrega (secundário, preservado)

Mais
  Resumo da semana
  Dias de funcionamento → mudanças / confirmação / turmas
  Produtos e fornecedores (também acessíveis no contexto)
  Registros anteriores
```

No computador, navegação horizontal persistente com quatro opções, rótulos visíveis e formulários com largura de leitura confortável. Poucos campos por etapa. No celular, os mesmos destinos e a mesma ordem, reorganizados para uma coluna. A proposta não depende de ícones sem texto nem de passar o mouse.

“Hoje” é o momento de organizar o trabalho, não a obrigação de lançar tudo na data atual. A ação continua sendo **Registrar um dia** e pede a data do resumo. Depois de salvar, o usuário vê exatamente qual dia foi registrado.

## Fluxos principais

### Registrar um dia

1. **Dia e troco:** escolher a data, registrar o troco e confirmar os responsáveis pela abertura/fechamento nos detalhes do dia. Reutilizar abertura já existente quando houver. Horários desconhecidos permanecem desconhecidos.
2. **Valores recebidos:** dinheiro, Pix, cartão e VR/VA. Mostrar a soma automaticamente. Campos vazios não viram zero. Zero significa que foi confirmado que não houve aquele recebimento.
3. **Conferir a gaveta:** valor retirado, valor contado, valor esperado e diferença. Mostrar a conta com palavras simples. A conferência é uma ação explícita; havendo diferença, pedir o que foi apurado e o encaminhamento.
4. **Confirmar:** indicar o dia salvo, total das vendas e o que ainda falta verificar. A falta de horário não pode produzir mensagem de conferência completa do funcionamento.

Se não souberem as retiradas, mostrar “Falta confirmar quanto foi retirado” e preservar o preenchimento. Não calcular a retirada pela diferença e salvá-la como se tivesse sido informada. Uma etapa só avança com os dados que exige; informações faltantes são apontadas junto ao campo.

O protótipo permite editar valores e navegar por três passos. Demonstra o estado com e sem diferença e soma as quatro formas de recebimento. A confirmação é apenas simulada.

### Registrar compra direta

1. Fornecedor, data, responsável e documento. Buscar fornecedor existente; cadastrar sem sair do fluxo se necessário.
2. Buscar os produtos cadastrados e informar quantidade/unidade e custo. Exibir o total calculado. Unidade de embalagem precisa ser legível; não converter pacote para kg sem regra existente.
3. Conferir o total da nota com os produtos. Exigir a explicação já prevista quando houver diferença.
4. Salvar a compra com seus efeitos de estoque e despesa uma única vez. Informar isso na confirmação.

Não obrigar a fabricar um pedido para a compra que já aconteceu. Pedidos reais anteriores mantêm seu caminho, com itens e quantidades restantes preenchidos no recebimento. Uma tentativa repetida após falha não pode criar outro pedido ou outro gasto.

### Contar produtos

Buscar → preencher somente os produtos contados → revisar quantidades e diferenças → confirmar data/hora e responsável → registrar. Itens em branco não mudam; zero é uma contagem válida. Não deduzir roubo, perda nem vendas da diferença. A proteção atual contra mudança de saldo durante a contagem permanece.

A primeira contagem aparece como preparação do sistema. Depois, os produtos com mínimo configurado e saldo já conferido podem indicar reposição. O sistema não deve esconder um saldo zero conhecido, nem tratar o catálogo não contado como uma lista de compras urgente.

### Conferir pendência e consultar semana

A pendência abre diretamente o dia, a nota ou o gasto. Mostra os registros já preenchidos e a ação disponível. Explicações e correções ficam no contexto; não é preciso procurar o mesmo registro em uma lista suspensa.

No resumo semanal: vendas informadas, compras e outros gastos, com período claro e aviso quando a semana estiver em andamento. Isso não é lucro: faltam custo dos produtos vendidos, estoque e outras apurações. Detalhe, comparações e relatório completo continuam acessíveis. Copiar texto não registra entrega; guardar a versão enviada continua sendo confirmação separada.

## Prioridade da tela inicial

Primeiro vem a tarefa habitual de transcrever o resumo. Em seguida, as duas ações ocasionais de compra e outro gasto. Pendências são específicas e não se repetem em vários cartões:

1. Valores ou registros incompletos que impedem a conferência do dia.
2. Diferença de caixa, possível duplicação e nota com divergência, sempre com data/nota e ação.
3. Mudança próxima de funcionamento que exige preparação.
4. Contagem e revisão semanal, com frequência e recência visíveis quando fizerem sentido.

Mostrar poucos itens e acesso ao restante; não esconder pendências antigas por causa dos limites atuais de sete ou quatorze dias. A quantidade máxima e o agrupamento exatos serão ajustados com os pais ao revisar o protótipo. Rotinas administrativas não devem gerar cinco cartões vermelhos no primeiro acesso.

Há dois cenários no seletor do protótipo: **Rotina em andamento** e **Primeiro uso**. São cenários para revisar o desenho, não estados lidos do banco.

## O que muda de lugar

| Recurso atual | Destino |
|---|---|
| Acompanhamentos da gestão | Tarefas contextualizadas em Hoje; diagnóstico completo consultável |
| Abertura, fechamento e conferência | Um percurso visual em Caixa; registros e validações preservados |
| Reabertura do caixa | Dentro do último dia elegível, com motivo; não aparece como ação diária |
| Despesas | Anotar outro gasto em Caixa e Hoje; histórico e alertas nos próprios registros |
| Pedidos e recebimentos | Compra direta como padrão; pedido anterior em seção secundária |
| Estoque e inventário | Produtos e contagem dentro de Compras; busca antes de listas extensas |
| Cadastro de item/fornecedor | No contexto da compra/produto e em Mais |
| Calendário completo e cursos | Dias de funcionamento em Mais; mudanças próximas sobem para Hoje |
| Relatório semanal completo | Resumo da semana em Mais; detalhar, exportar e versões em segundo plano |
| Critérios dos alertas e fórmulas | Explicação do alerta/detalhe do registro |
| Grandes tabelas históricas | Consultas com busca e período, não no início de cada tela |

Sai da interface principal: contadores de cadastros sem utilidade na tarefa, percentual genérico de rotinas “em dia”, comparações sem contexto, controles destrutivos separados do registro, baixar Markdown como escolha de primeiro nível e avisos explicativos repetidos. **Nenhum desses dados ou recursos será apagado.**

## Apoio necessário da API, a discutir junto à implementação

Esta proposta não é viável apenas reorganizando JSX. Algumas limitações existentes precisam de apoio específico, sem mudar as contas da cantina:

1. **Horário desconhecido.** `CashSession` e as APIs hoje exigem instantes de abertura e fechamento. É preciso representar a informação que falta e distinguir dia operacional, horário real e momento do lançamento. Nunca gravar horário contratual como horário informado. A comparação 07h30/22h continua para horários reais conhecidos; desconhecidos geram conferência pendente. A estratégia de migração deve conservar todos os horários existentes como conhecidos e preservar a regra de sequência entre caixas com dados suficientes.
2. **Compra direta.** A API atual só recebe contra pedido existente. Criar um percurso transacional para compra direta, que persista os registros internos necessários e estoque/despesa juntos, com prevenção de duplicidade, sem inventar um custo estimado histórico para gerar comparações artificiais. Pedidos reais, entregas parciais e regras da nota continuam disponíveis.
3. **Completude da contagem.** Distinguir item ainda não contado de item com saldo confirmado. Usar evidências existentes de movimento/contagem e expor essa situação de forma consistente, sem mudar saldos nem o mínimo cadastrado. A regra atual de `saldo <= mínimo` permanece no diagnóstico completo; a recomendação principal precisa informar quando o saldo ainda não foi confirmado. As contagens parciais não podem marcar todo o estoque como conferido.
4. **Composição do registro do dia.** Preservar abertura, fechamento e conferência como operações de negócio, com seus limites atuais. Ao apresentar um percurso único, retomar o registro já criado após falha, bloquear envios repetidos e nunca indicar sucesso completo quando somente uma etapa foi gravada. Eventual estado de preenchimento incompleto deve ser representado explicitamente, sem dados fictícios para satisfazer campos obrigatórios.
5. **Consultas e pendências.** Não prometer histórico integral com as listas atuais limitadas a 60/300 registros e períodos fixos de consulta. Usar filtros e paginação no servidor se forem necessários; não somar resultados truncados como se fossem todos os dados.

As fórmulas de dinheiro, valores monetários em centavos, estoque por movimentos, proteção contra estoque negativo, controle de contagem concorrente, documento duplicado, conferência de notas, alertas de gastos, reabertura limitada e registro das versões dos relatórios continuam sendo regras a preservar. Nenhuma migração foi aplicada nesta etapa.

## Aparência e comportamento

Fundo claro, verde já presente na identidade e superfícies de leitura simples. Texto principal entre 17 e 18 px, botões com ao menos 48 px de altura, foco de teclado visível e estados indicados por texto além da cor. Tabelas ficam nas consultas, não dentro de cada tarefa principal.

Uma ação principal por etapa. Valores calculados aparecem quando ajudam a conferir, não em painéis de indicadores. Erros indicam o campo e preservam o preenchimento. Mensagens distinguem carregando, sem registro e falha; uma falha de busca não pode aparecer como “nenhuma pendência”.

## Como revisar antes de implementar

O protótipo mostra Hoje, Caixa, registro de dia em três passos, gasto, Compras, compra direta, contagem, Mais, semana, funcionamento e conferência de diferença. As telas secundárias mostram seu propósito e posição; não pretendem ser formulários finais. Busca de produto, soma de vendas, conta da gaveta e comparação da nota são demonstráveis. Salvar apenas simula o resultado; não chama o sistema.

Sugestão de revisão com os pais: registrar um dia pelo resumo, lançar uma nota sem pedido anterior e encontrar um produto para contar. Verificar se entendem os rótulos sem ajuda e se conseguem explicar a diferença na gaveta. Ajustar a proposta com base nessas tarefas antes de integrar o código.

Após a definição: implementar toda a navegação e os fluxos em conjunto, realizar os apoios de API necessários com migrações aditivas e backup, manter os caminhos secundários, testar as regras de negócio e validar telas com os casos completos, incompletos, vazios e de falha. A implementação ainda depende da definição desta proposta pelo usuário, conforme solicitado na tarefa.

## Verificação desta proposta

Protótipo aberto no Chrome local. Conferidas onze telas em 1365 px e 390 px, sem rolagem horizontal. Exercitados os passos de registro, soma dos recebimentos, cálculo de diferença na gaveta, explicação de divergência da nota, busca sem acentos e separação do primeiro uso. Capturas de Hoje, registro do dia, compra, contagem e celular estão nesta pasta. Nenhuma gravação foi feita na API nem no banco durante essa verificação. Isso verifica a apresentação e as interações demonstradas, não a integração futura ou a validação com os pais.
