# Projeto inicial de gestão da cantina

Versão de 7 de novembro de 2026. Plano de trabalho para implantação, sujeito ao levantamento da operação.

## 1. Objetivo e informações disponíveis

Organizar as vendas, o estoque, a produção, o dinheiro e a equipe para identificar diferenças, reduzir perdas, atender bem e acompanhar a remuneração do gestor.

Informado pelo gestor:

- A cantina funciona dentro do Senai em Paulista. O pai do gestor ganhou a licitação, e pai e mãe acompanharão os resultados e realizarão seus pagamentos.
- A operação tem cerca de três meses. Segundo o gestor, atualmente se paga; isso ainda precisa ser confirmado por registros de receitas, custos e despesas.
- O público é formado principalmente por alunos, além de funcionários e soldados que fazem curso técnico. O movimento diminui nas férias.
- Funciona de segunda a sexta, da manhã à noite, fechando em feriados e fins de semana. Os intervalos das aulas concentram picos pela manhã, à tarde e à noite.
- Vende almoço em marmita de tamanho fixo, doces, balas, lanches, bolos, salgados, sucos e outros itens. O cardápio completo ainda será levantado.
- O gestor pretende acompanhar estoque e dinheiro principalmente à distância, com o mínimo possível de visitas. Não poderá comparecer pela manhã por causa das aulas e também terá demandas da faculdade.
- Há autonomia para propor e executar mudanças, comunicando os pais e avaliando a viabilidade. Alguns preços são fixados pelas condições da licitação, como o refrigerante em lata a R$ 4, conforme informado. A lista completa ainda será fornecida pelo pai.
- Existe uma maquininha em uso e não há controle de estoque.
- Chegará uma solução Stone apresentada como tendo controle de estoque e de despesas. O modelo, o aplicativo e o plano ainda precisam ser identificados.
- Quantidade de funcionários, vendas diárias e custos ainda serão levantados.
- Haverá uma meta. A informação inicial é de que o gestor receberá o valor que ultrapassar essa meta, mas a base de cálculo ainda precisa ser confirmada.
- Há suspeita de desvios ou de porções acima do padrão. Isso ainda não constitui uma conclusão sobre funcionários.
- A suspeita surgiu de despesas que não fechavam e de uma estimativa de estoque feita pelo pai, sem inventário formal.
- Uma pessoa de confiança já acompanha a operação, mas também tem tarefas de cozinha e não mantém os controles de forma suficiente. O pai dividia a administração com outras atividades.
- O pagamento ocorre antes da entrega e quem entrega consegue conferir. Os comprovantes ficam no local, mas o fechamento do caixa não tem controle adequado.
- Dona Gel é a referência local e já informa a lista de compras, normalmente para reposição no fim de semana ou início da semana seguinte. Ela também faz algumas compras no atacado. Segundo o esclarecimento posterior, quando falta um item a equipe normalmente informa a falta e compra no dia seguinte, em vez de comprar imediatamente.
- O pai solicita refrigerantes à Coca-Cola. O gestor e o pai levam mercadorias para a cantina; o gestor também transporta os refrigerantes quando chegam.
- São aceitos dinheiro, Pix e cartão. Os recebimentos digitais da máquina vão para uma conta acompanhada pelo pai. O dinheiro em espécie fica no caixa e está sem conferência presencial do pai há algum tempo.
- O gestor terá acesso aos registros digitais e deseja um sistema em Python, com armazenamento local no próprio computador.
- O sistema deverá indicar o responsável pelo caixa conforme dia e horário, permitindo substituição manual. Ainda faltam os nomes e horários da escala.
- O gestor considera reservar duas a três horas diárias para a administração. Não deseja trabalhar à noite nem comparecer pela manhã. As visitas devem ser planejadas à tarde.
- As despesas são pagas pelos pais e pela própria cantina. O gestor atuará como gerente e receberá o excedente da meta; a base e o valor da meta continuam pendentes.
- O canal preferido para Dona Gel é mensagem privada pelo WhatsApp do próprio celular. Na proposta inicial, o gerente recebe a informação e a lança no sistema local; não há leitura automática de conversas implementada.
- Dona Gel é a única pessoa que o gestor identifica neste momento como possível responsável pela contagem no encerramento. Seu horário e disponibilidade no fechamento ainda precisam ser confirmados.
- Nas compras pagas por Dona Gel, ela guarda a nota e informa a compra; o pai geralmente a reembolsa por Pix. Registrar compra e pagamento vinculados, evitando reconhecer a despesa novamente ao reembolsar.
- Refeições da equipe, cortesias e fiado ainda precisam ser esclarecidos.
- Está prevista a instalação de câmeras pela empresa.

Este documento define o projeto de gestão e os registros necessários. Ainda não é um sistema conectado à Stone nem uma planilha com dados reais.

## 2. O que o trabalho do gestor inclui

| Frente | Trabalho do gestor | Evidência de acompanhamento |
|---|---|---|
| Vendas e atendimento | Conferir registro dos itens, preços, descontos e entrega dos pedidos | Vendas por produto, horário, operador e forma de pagamento |
| Compras e estoque | Planejar compras, conferir recebimento, registrar movimentações e contar produtos | Documento do fornecedor, ficha de estoque e contagem física |
| Produção | Planejar quantidades, padronizar receitas e porções e medir sobras | Ficha técnica e registro da produção por lote |
| Caixa e bancos | Conferir dinheiro, Pix, cartões, despesas e valores a receber | Fechamento do turno, extratos e comprovantes |
| Equipe | Organizar escala, funções, treinamento, passagem de turno e rotina de higiene | Escala, responsáveis e listas de conferência |
| Resultado mensal | Apurar vendas, custos, despesas e remuneração conforme acordo | Relatório mensal conciliado com os registros de origem |
| Aumento de vendas | Identificar horários de maior procura, faltas de produtos e oportunidades comerciais | Comparação de vendas, margem e perdas antes e depois das ações |

Combinar com o proprietário quais decisões o gestor poderá tomar: comprar, negociar, alterar preço, conceder desconto, definir cardápio, autorizar cancelamentos e organizar a equipe. Responsabilidade e acesso às informações precisam acompanhar essa autonomia.

Atualização: o gestor relatou autonomia, com comunicação e avaliação das mudanças com os pais. A atuação será principalmente remota. Portanto, tarefas físicas de recebimento, contagem, pesagem e fechamento precisam ter responsáveis presentes, enquanto o gestor acompanha os registros, aprova decisões e revisa diferenças. A autonomia de preços deve respeitar a lista de valores fixados na licitação.

## 3. Definir a meta e a remuneração

Antes de usar qualquer valor como salário previsto, registrar o acordo e esclarecer:

1. A meta é sobre vendas, recebimentos ou lucro? Se for vendas, quais descontos, devoluções e impostos alteram a base?
2. O período será mensal? Quais as datas de início e encerramento?
3. Quem paga mercadorias, salários, taxas da maquininha, energia, aluguel e demais despesas?
4. Existe parte fixa ou valor mínimo? O que acontece em um mês abaixo da meta?
5. Quando ocorre o pagamento e qual relatório comprova a apuração?
6. Como entram férias escolares, feriados, início no meio do mês e fechamento extraordinário?
7. A meta poderá mudar? Com qual antecedência e como isso será registrado?
8. Como serão tratados cancelamentos e devoluções descobertos depois do fechamento?

Validar a formalização com os responsáveis pelo contrato e pela contabilidade. Não presumir que a explicação inicial resolve todas essas condições.

Se o acordo confirmar 100% do excedente de faturamento:

**Parcela variável = máximo entre zero e (faturamento elegível do período − meta do período).**

Exemplo ilustrativo, sem representar a meta real:

| Meta | Faturamento elegível | Parcela variável pela regra descrita |
|---:|---:|---:|
| R$ 50.000 | R$ 49.000 | R$ 0 |
| R$ 50.000 | R$ 50.100 | R$ 100 |
| R$ 50.000 | R$ 60.000 | R$ 10.000 |

Esses valores não afirmam que a remuneração total possa ser zero. A existência de parte fixa e as condições contratuais ainda estão em aberto.

Se a regra for sobre lucro, primeiro será necessário definir exatamente o resultado usado na conta e quais custos e despesas serão considerados. Não trocar a base automaticamente.

**Consequência prática:** economizar R$ 1.000 em ingredientes, mantendo as mesmas vendas, melhora o resultado da cantina. Se a remuneração depender exclusivamente do excedente de faturamento, essa economia não acrescenta R$ 1.000 à parcela variável.

Faturamento representa vendas do período. Fluxo de caixa acompanha recebimentos e pagamentos. Uma venda no cartão pode ser realizada em um mês e recebida em outro. O lucro exige considerar custos e despesas. [Referência: Sebrae, gestão financeira](https://meuatendimento.sebrae.com.br/sites/PortalSebrae/artigos/como-fazer-a-gestao-financeira-do-pequeno-negocio%2Cd999a442d2e5a410VgnVCM1000003b74010aRCRD).

## 4. Entrada da Stone na operação

Usar o sistema contratado como registro principal das vendas, se ele atender às necessidades abaixo. Evitar redigitar manualmente cada venda em outro lugar. Complementar somente os controles que faltarem.

A Stone documenta o cadastro de produtos no Catálogo, com nome, preço, código de barras, categoria e estoque. Isso não confirma, por si só, o consumo automático dos ingredientes de cada marmita no pacote contratado. [Referência: Stone, configurar produtos](https://ajuda.stone.com.br/catalogo-stone/configurar-produtos).

### Conferir na implantação

- Nome do modelo, do aplicativo de gestão, do plano e dos serviços contratados.
- Cadastro separado para marmitas por tamanho, adicionais, bebidas, lanches e embalagens cobradas.
- Registro de vendas em dinheiro e Pix, além de cartões, sem duplicar a venda na conferência bancária.
- Estoque de mercadorias em unidades e, se disponível, ingredientes em kg, g e litros.
- Ficha técnica: verificar se uma marmita pode consumir quantidades definidas de vários ingredientes.
- Baixa por produção ou por venda: definir um único método para cada etapa, evitando descontar o mesmo ingrediente duas vezes.
- Registro de perdas, refeições da equipe, cortesias, devoluções e inventário.
- Identificação do operador e permissões para alterar preços, cancelar vendas e ajustar estoque.
- Histórico de alterações e exportação dos relatórios para conferência e arquivo.
- Tratamento de falta de internet, venda não sincronizada, estorno e pagamento dividido.
- Despesas pagas fora da conta Stone e contas a pagar, se esses recursos estiverem disponíveis.

### Teste acompanhado antes de confiar nos saldos

1. Cadastrar um produto com estoque inicial conhecido.
2. Fazer venda de teste pelo procedimento orientado pelo suporte, verificando baixa e registro do pagamento.
3. Testar cancelamento e conferir se a venda e o estoque ficam corretos, inclusive quando o produto não retorna fisicamente.
4. Conferir uma venda em dinheiro e uma em Pix no fechamento.
5. Se houver ficha técnica, testar uma receita e verificar os ingredientes e unidades descontados.
6. Comparar o relatório com a contagem física e os comprovantes do teste.

Documentar o resultado. Recursos ausentes viram controles complementares simples; não se presume integração sem teste.

O “Total de Entradas” do Minhas Finanças pode incluir transferências e créditos de empréstimos, além de vendas líquidas recebidas. Portanto, não deve ser adotado automaticamente como faturamento para calcular a remuneração. [Referência: Stone, Minhas Finanças](https://www.stone.com.br/financas).

## 5. Estoque: começar por uma contagem real

No início da gestão, realizar contagem acompanhada e registrar a data de corte. Identificar mercadorias vencidas, embalagens abertas, ingredientes em preparação e produtos prontos separadamente. Registrar também as diferenças herdadas, para não atribuí-las automaticamente à gestão nova.

Para cada item, cadastrar código, descrição, unidade de controle, custo, fornecedor, local, lote, validade e estoque mínimo. O mínimo será definido a partir do consumo observado, prazo de reposição e capacidade de armazenamento, sem inventar um percentual único para todos os produtos.

Converter unidades de compra: uma caixa com 12 bebidas dá entrada em 12 unidades, não em uma unidade. Manter pesos brutos, pesos aproveitáveis e pesos preparados identificados.

**Saldo esperado do item = saldo inicial + entradas + devoluções ao estoque − saídas registradas.**

As saídas devem distinguir venda direta, consumo na produção, perda, refeição da equipe, cortesia e devolução ao fornecedor. Transferências entre locais devem aparecer nos dois lados, sem serem tratadas como consumo da cantina inteira.

**Diferença de inventário = quantidade contada − saldo esperado.**

Diferença negativa indica falta em relação ao registro; diferença positiva também deve ser explicada. Conferir documento, unidade, data e movimentação antes de ajustar. Todo ajuste deve ter motivo, responsável e aprovação.

Proposta de frequência inicial: conferir diariamente itens caros ou de giro rápido, como proteínas e bebidas, e realizar uma contagem geral semanal. Ajustar a frequência após conhecer o tamanho da operação. Priorizar o uso dos lotes com vencimento mais próximo, respeitando suas condições de conservação.

## 6. Marmitas: receita, rendimento e porção

Criar ficha técnica para cada tamanho e opção. Ela deve informar ingredientes, quantidades, etapas, rendimento medido, peso servido por componente, embalagem e custo. O Sebrae recomenda ficha técnica para padronizar o preparo e controlar os insumos. [Referência: Sebrae, ficha técnica](https://www.sebraepr.com.br/comunidade/artigo/ficha-tecnica-o-que-e-e-por-que-um-restaurante-precisa-ter).

Para implantar:

1. Medir quanto de ingrediente sai do estoque para um lote.
2. Pesar o produto aproveitável e o produto pronto, identificando perdas normais de limpeza e preparo.
3. Medir o rendimento e definir a porção com o responsável pelo cardápio.
4. Padronizar utensílios e usar balança com tara da embalagem.
5. Conferir amostras ao longo do serviço e registrar desvios para treinamento.
6. Registrar refeições vendidas, refeições da equipe, cortesias, perdas e sobras.

Exemplo exclusivamente de cálculo: se o padrão definido for 120 g de proteína **pronta** e forem servidas 100 marmitas iguais, são esperados 12 kg de proteína pronta. Se a média efetiva for 150 g, seriam 15 kg, ou 3 kg a mais. Isso aponta necessidade de apuração do porcionamento; não comprova furto. Não comparar esses 12 kg diretamente com carne crua sem medir o rendimento.

Em um modelo com registro por produção, o ingrediente sai quando o lote é preparado e o produto pronto entra no estoque correspondente. A venda baixa o produto pronto. Não baixar novamente o ingrediente na venda. Sobras e perdas precisam ter movimentação própria.

**Produtos prontos disponíveis = saldo inicial de prontos + produção.**

**Produtos prontos disponíveis = vendas entregues + refeições da equipe + cortesias + perdas + saldo final de prontos.**

Para preparações servidas em peso, conciliar em peso e converter em porções pelo padrão medido. Cada uso deve ter uma classificação única para evitar dupla contagem.

## 7. Caixa: conferir separadamente cada meio de pagamento

Toda venda deve registrar os itens e a forma de pagamento. Cobrar um valor na maquininha sem informar os produtos pode comprovar o recebimento, mas não explica o estoque consumido.

Por turno, registrar operador, abertura, vendas, devoluções, despesas, reforços de troco, retiradas e fechamento.

**Dinheiro esperado na gaveta = abertura + recebimentos em espécie + reforços − devoluções em espécie − despesas pagas pela gaveta − retiradas.**

**Diferença de caixa = dinheiro contado − dinheiro esperado.**

Conferir Pix pelo crédito efetivo e vínculo com a venda. Conferir cartão por transação aprovada, taxa, previsão de recebimento e crédito efetivo. Não somar novamente o recebimento bancário ao faturamento de uma venda já registrada. Pagamento dividido deve gerar uma venda com suas parcelas por meio de pagamento.

Retiradas e depósitos entre gaveta e banco são transferências internas, não novas vendas nem despesas operacionais. Aporte do proprietário e empréstimo também não são vendas. Registrar saídas com documento e finalidade, inclusive compras emergenciais.

Manter contas a pagar e a receber por vencimento. A conferência dos recebimentos deve seguir o calendário de liquidação do cartão, inclusive quando houver antecipação.

## 8. Equipe e apuração de ocorrências

- Definir responsáveis por receber mercadoria, guardar, produzir, vender e fechar o turno.
- Registrar passagem de turno com dinheiro, pendências e divergências.
- Usar acessos individuais quando o sistema permitir e limitar ajustes, descontos e cancelamentos.
- Quando a equipe for pequena, compensar o acúmulo de funções com revisão do gestor ou do proprietário.
- Registrar refeições e retiradas autorizadas da equipe, com uma regra conhecida por todos.
- Treinar o padrão das porções e conferir se utensílios e balança permitem cumpri-lo.
- Registrar ocorrências com data, item, quantidade, evidências, explicação, responsável pela revisão e providência.

Sequência de apuração proposta: recontar; conferir unidades e documentos; revisar perdas e produção; comparar vendas e pagamentos; ouvir o responsável; definir correção. A diferença deve ser tratada como pendência até a causa ser esclarecida.

As câmeras podem apoiar a revisão de ocorrências específicas pelo responsável autorizado. Elas não medem sozinhas o peso servido nem substituem os registros. Definir com a empresa as regras de uso, privacidade, acesso e conservação das imagens.

Incluir rotina de recebimento, validade, armazenamento, higiene e controles de tempo e temperatura aplicáveis. Estruturar esses procedimentos com o responsável pela segurança dos alimentos e as orientações da vigilância local. A cartilha da Anvisa aborda boas práticas desde os ingredientes até o serviço. [Referência: Anvisa, cartilha de boas práticas](https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/alimentos/manuais-guias-e-orientacoes/cartilha-boas-praticas-para-servicos-de-alimentacao.pdf).

## 9. Relatórios que o gestor precisa enxergar

| Frequência | Informações | Decisão que ajuda a tomar |
|---|---|---|
| Diária | Vendas por produto e horário, quantidade de pedidos e valor médio por pedido | Preparar o próximo serviço e organizar atendimento |
| Diária | Produção, vendas entregues, refeições da equipe, sobras e perdas | Ajustar produção e porções |
| Por turno | Caixa esperado, contado e diferenças por meio de pagamento | Resolver pendências enquanto os fatos estão recentes |
| Semanal | Contagem, divergências, vencimentos e itens em falta | Comprar melhor e investigar perdas |
| Mensal | Vendas, deduções, consumo de estoque, despesas, taxas e resultado | Avaliar a operação e as ações comerciais |
| Mensal | Base contratada, meta, excedente, parcela variável e data de pagamento | Comprovar a apuração da remuneração |

Valor médio por pedido = vendas após descontos e cancelamentos ÷ quantidade de pedidos válidos. Não dividir por quantidade de itens.

Se a meta for de faturamento, acompanhar quanto falta e os dias de funcionamento restantes. Uma média diária necessária pode orientar o acompanhamento, mas deve considerar que dias da semana, férias e eventos têm demandas diferentes. Projeção não é valor já ganho. Se a meta não estiver definida, exibir “meta pendente”, sem usar zero como meta.

No fechamento mensal, apurar o consumo a custo com estoque inicial + compras líquidas − estoque final, considerando também preparações e produtos prontos e ajustando transferências externas quando existirem. Separar perdas para análise, sem descontá-las duas vezes no resultado. O pagamento de uma compra afeta o caixa; a mercadoria ainda guardada não foi toda consumida naquele mês.

Mostrar o resultado antes e depois da remuneração variável do gestor quando aplicável. O proprietário precisa avaliar se a regra de pagamento permite sustentar a operação. A definição da base é necessária antes de calcular essa parcela.

## 10. Roteiro de implantação em 30 dias

Cronograma proposto. Ajustar à chegada do equipamento e à disponibilidade dos registros.

| Período | Ações | Entrega esperada |
|---|---|---|
| Dias 1 a 3 | Levantar equipe, funcionamento, cardápio, preços, fornecedores, despesas e relatórios existentes. Contar estoque e caixa na entrada da gestão | Registro inicial acompanhado, pendências e responsáveis definidos |
| Dias 4 a 7 | Identificar e testar a solução Stone. Cadastrar produtos e unidades. Iniciar fechamento por turno e registro de perdas | Vendas e caixa conferidos diariamente, com estoque inicial cadastrado |
| Dias 8 a 14 | Medir receitas, rendimento, porções e produção. Priorizar proteínas, marmitas e bebidas | Fichas dos principais produtos e primeira conciliação semanal |
| Dias 15 a 21 | Investigar diferenças, corrigir cadastros e treinar a equipe. Ajustar compras ao consumo observado | Causas documentadas e controles corrigidos |
| Dias 22 a 30 | Consolidar vendas, estoque, despesas e pendências. Revisar a regra da meta com o proprietário | Primeiro relatório gerencial e plano de ações do mês seguinte |

Não definir uma meta de redução de perdas sem uma medição inicial confiável. Primeiro medir, depois combinar a melhoria esperada.

## 11. Registros mínimos para planilha ou sistema complementar

Esses campos são uma especificação para a próxima etapa, não formulários já implementados.

| Registro | Campos mínimos |
|---|---|
| Produtos e insumos | Código, descrição, categoria, unidade, custo, preço de venda quando aplicável, mínimo, fornecedor |
| Movimentação de estoque | Identificador, data/hora, item, local, lote/validade, tipo, quantidade, unidade, documento, motivo, responsável |
| Inventário | Data/hora de corte, item, local, saldo esperado, quantidade contada, diferença, apuração e aprovação |
| Ficha técnica | Produto, versão, ingredientes, unidades, quantidades, rendimento, porção pronta, embalagem e custo |
| Produção | Data/turno, lote, receita/versão, ingredientes consumidos, rendimento, destino e responsável |
| Venda | Identificador, data/hora, itens, quantidades, preços, descontos, estado da venda, operador e pagamentos vinculados |
| Despesa | Identificador, categoria, descrição, competência, vencimento, data de pagamento, valor, meio, documento e responsável |
| Fechamento | Data/turno, operador, abertura, movimentos em espécie, valores por meio, contagem, diferenças e conferente |
| Equipe | Nome, função, escala, responsabilidades e treinamentos, com acesso restrito aos dados necessários |
| Meta e remuneração | Período, base acordada, valor da meta, regra vigente, resultado elegível, parcela apurada, aprovação e pagamento |

Manter identificadores da venda e da transação no arquivo exportado para conciliar sem duplicidade. Guardar os arquivos de origem e comprovantes em pastas por mês, com acesso adequado e cópia de segurança.

## 12. Aumentar o faturamento com controle

Depois de organizar os registros, avaliar disponibilidade dos produtos mais procurados, rapidez da fila, encomendas de almoço e oferta de complementos ou combos com custo calculado. Confirmar as permissões comerciais e as regras da instituição onde a cantina funciona.

Medir cada ação comparando dias equivalentes: pedidos, valor médio por pedido, custo dos itens vendidos, perdas e capacidade de atendimento. Um desconto pode aumentar unidades vendidas e reduzir o resultado. Evitar comprar ou produzir mais sem evidência de demanda.

## 13. Próximas informações a levantar

- Nome exato do sistema que chegará com a Stone e funcionalidades incluídas.
- Horários exatos de abertura, encerramento e intervalos, além do calendário de férias e feriados da instituição.
- Equipe por função e turno, com responsável local disponível para os registros em cada período.
- Cardápio e preços, incluindo tamanhos das marmitas e adicionais.
- Lista de preços fixados pela licitação e itens com preço ajustável. Foi informado que há um tamanho fixo de marmita.
- Histórico de vendas disponível, separado por dinheiro, Pix e cartões quando possível.
- Lista de fornecedores, compras, despesas e contas pendentes.
- Contagem inicial e recursos disponíveis para pesar e armazenar.
- Acordo da meta, remuneração e autonomia do gestor.
- Categorias e valores das despesas, pagas pelos pais e pela cantina conforme informado. Confirmar no acordo o tratamento de eventuais diferenças, sem presumir desconto da remuneração.
- Quem recebe e confere as entregas, quem opera e fecha o caixa, quem cobre Dona Gel e quem recolhe o dinheiro em espécie.
- Formato das mensagens de Dona Gel pelo WhatsApp, lançadas pelo gerente no computador, e quem enviará registros nos demais turnos.
- Horário da janela de administração à tarde e frequência viável das visitas.

O controle pode começar antes de conhecer a meta: contagem inicial, registro de todas as vendas, movimentação dos produtos, fechamento diário e medição das porções.

## 14. Modelo de acompanhamento à distância

Proposta a validar com o gestor e com a equipe. Não há ainda definição dos responsáveis nem da carga de trabalho de cada pessoa.

| Momento | Responsável presente | Acompanhamento do gestor |
|---|---|---|
| Abertura | Registrar troco, pendências e disponibilidade dos itens prioritários | Consultar depois, em horário compatível com a faculdade |
| Recebimento | Conferir quantidade e condição da mercadoria contra o documento, antes de dar entrada | Revisar compras, preços e diferenças documentadas |
| Produção e atendimento | Registrar produção, perdas, consumo da equipe e vendas pelos procedimentos definidos | Conferir consistência e indicadores nos horários combinados |
| Troca de turno | Registrar entrega de caixa, pendências e passagem de responsabilidade | Revisar diferenças e aprovações que não sejam urgentes |
| Encerramento | Contar dinheiro, registrar retiradas e enviar fechamento, com documentos de apoio | Conciliar na próxima janela de administração, preservando a data do turno de origem |
| Contagem periódica | Contar os itens definidos e registrar o horário de corte | Comparar com o saldo esperado e realizar conferências presenciais por amostragem quando necessário |

Para funcionar, o modelo precisa de uma pessoa responsável em cada turno, tarefas compatíveis com sua disponibilidade e acesso do gestor aos relatórios de vendas, estoque e finanças. Não atribuir automaticamente todas as novas tarefas à pessoa que já cuida da cozinha.

O gestor não terá presença física pela manhã e não deseja trabalho à noite. Definir quem resolve problemas imediatos nesses períodos e quais assuntos aguardam a próxima janela de administração à tarde. O fechamento da noite precisa ser executado e guardado por um responsável no local. Combinar também um substituto para ausências e um procedimento para falhas de internet ou equipamento.

Uma implantação inicial pode exigir visitas adicionais à tarde para cadastrar, contar estoque, medir porções e treinar os responsáveis. Frequência e duração ainda precisam ser combinadas. Depois, ajustar as visitas aos resultados das conferências, preservando checagens físicas periódicas. Planejar a rotina dentro da disponibilidade proposta de duas a três horas diárias, validando esse tempo durante a implantação.

Prioridades da primeira etapa: identificar responsáveis por turno, fazer o inventário inicial acompanhado, separar preços fixos e ajustáveis, testar a Stone, fechar o caixa diariamente e registrar as compras. As diferenças antigas devem ser documentadas como pendências de origem, sem serem apresentadas como furto comprovado.

## 15. Sistema local em Python

Requisito solicitado pelo gestor: guardar informações localmente no próprio computador e acompanhar estoque, dinheiro, despesas, equipe e meta. A especificação inicial está em `ESPECIFICACAO_SISTEMA_PYTHON.md`. A implementação ainda não foi iniciada; a definição do envio de informações do local para o computador é uma dependência importante.
