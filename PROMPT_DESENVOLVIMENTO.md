# Prompt para desenvolver a cantina por etapas

> Este é o prompt inicial do planejamento. O sistema já avançou: antes de executar qualquer etapa, leia `ESTADO_DO_PROJETO.md`. O usuário pediu para parar após o commit da importação CSV; a continuidade depende de uma nova solicitação.

Copie o texto abaixo para o agente no VS Code. Ele contém o contexto, as regras e a primeira tarefa.

---

Você será meu parceiro de desenvolvimento de um sistema de gestão de cantina. Quero construí-lo devagar, com etapas pequenas, funcionais e verificáveis. Responda em português e explique decisões importantes de forma simples.

## Como trabalhar

- Leia as instruções do repositório e os arquivos PROJETO_GESTAO_CANTINA.md, ESPECIFICACAO_SISTEMA_PYTHON.md e PERGUNTAS_PARA_O_PAI.md, se existirem.
- Inspecione o código e o ambiente antes de modificar. Já podem existir package.json, arquivos de dependências, ambientes virtuais e instalações preliminares. Isso não significa que a aplicação esteja implementada ou executável.
- A escolha atual é Python + React + PostgreSQL local. Ela substitui qualquer menção anterior a SQLite.
- Implemente somente a etapa solicitada. Na primeira interação, execute apenas a etapa 1 abaixo. Não construa todos os módulos de uma vez.
- Faça alterações pequenas, com organização simples. Não adote microsserviços ou infraestrutura desnecessária.
- Não apague nem sobrescreva trabalho existente sem examiná-lo. Não altere dados reais para executar testes.
- Resolva decisões técnicas comuns com bom senso. Pergunte quando faltar uma regra de negócio que realmente impeça a etapa, sem repetir perguntas já respondidas nos documentos.
- Ao terminar a etapa, informe o que funciona, como executar e testar no Windows, quais testes foram feitos e o que falta. Registre isso em ESTADO_DO_PROJETO.md e encerre a etapa. A próxima será uma nova solicitação minha.
- Se outro agente já modificou arquivos, leia o diff e o estado do projeto antes de continuar. Não trabalhe simultaneamente nos mesmos arquivos que outro agente.

## Contexto da cantina

Meu pai ganhou uma licitação para operar uma cantina dentro do Senai em Paulista. Ela funciona há aproximadamente três meses. Meus pais acompanharão meus resultados e pagarão minha remuneração.

Atende principalmente alunos, além de funcionários e soldados em curso técnico. Funciona de segunda a sexta, da manhã à noite, com picos nos intervalos. Fecha em feriados e fins de semana, e o movimento diminui nas férias.

Vende marmita de tamanho fixo, lanches, salgados, bolos, doces, balas, sucos, refrigerantes e outros produtos. O cardápio completo ainda será levantado. Alguns preços são fixados pela licitação: segundo a informação atual, refrigerante em lata custa R$ 4. A tabela oficial ainda será fornecida. Outros preços podem ser ajustados, comunicando meus pais e avaliando a viabilidade.

Atuarei como gerente de estoque e dinheiro, principalmente à distância. Pretendo dedicar duas a três horas por dia, preferencialmente à tarde. Não posso comparecer pela manhã e não quero trabalhar à noite. Visitas devem ser planejadas à tarde. O fechamento noturno precisará ser feito por alguém presente, para minha conferência posterior.

Dona Gel é a referência local e também trabalha na cozinha. Envia a lista de compras pelo WhatsApp particular e prefere continuar assim. Eu ou meu pai levamos os produtos. Meu pai solicita refrigerantes à Coca-Cola. Quando Dona Gel compra com dinheiro próprio, guarda a nota e meu pai normalmente a reembolsa por Pix. Quando falta um item, a equipe geralmente avisa e a compra fica para o dia seguinte.

Recebemos em dinheiro, Pix e cartão. Os recebimentos digitais vão para uma conta acompanhada pelo meu pai; terei acesso. Dinheiro em espécie fica no caixa e atualmente não tem conferência confiável. O cliente paga antes de retirar o pedido.

Chegará uma solução Stone apresentada como tendo estoque e despesas, mas modelo, aplicativo, plano, relatórios e integrações ainda são desconhecidos. Não presuma acesso a API, webhook, ficha técnica ou baixa automática de ingredientes.

Há suspeitas de perdas ou desvios, baseadas em contas inconsistentes e estimativas de estoque, sem controle histórico suficiente. O sistema deve registrar diferenças e evidências, sem tratar uma diferença como prova automática de furto.

As despesas são dos meus pais e da cantina. Minha remuneração será o excedente de uma meta, mas ainda não sabemos o valor nem se a base será faturamento, recebimentos ou lucro. Quantidade de funcionários, escalas, vendas, custos e regras de consumo da equipe também estão pendentes.

## Stack e execução

- Backend: Python com FastAPI, SQLAlchemy, Alembic e validação de dados.
- Frontend: React com TypeScript e Vite.
- Banco: PostgreSQL local. Não substituir silenciosamente por SQLite.
- Uso inicial no Windows, com API e interface acessíveis apenas localmente.
- Verifique versões e compatibilidade das dependências e preserve arquivos de lock.
- Inspecione como o PostgreSQL pode rodar neste computador. Reaproveite uma instalação adequada ou documente uma configuração local reproduzível. Não presuma que Docker esteja instalado.
- Use variáveis de ambiente e .env.example, sem versionar credenciais.
- Mantenha os dados ativos do PostgreSQL fora do OneDrive e use ferramentas adequadas para backup consistente.
- A interface deve ser clara, responsiva e em português brasileiro, com valores em reais, estados vazios e mensagens de erro úteis.

## Regras essenciais dos módulos futuros

1. Caixa: distinguir responsável previsto pela escala de responsável confirmado. Calcular o previsto por dia e horário, considerando dias fechados. Permitir substituição manual com motivo e histórico. Sem confirmação, mostrar essa pendência. Alterar a escala não deve reatribuir operações antigas.
2. Atualização: mostrar quando os dados foram registrados. Escala automática não comprova presença. Um sistema local só conhece informações da cantina que tenham sido enviadas e lançadas.
3. WhatsApp: inicialmente, Dona Gel envia mensagens e comprovantes e eu faço os lançamentos. Não implementar leitura automática de conversas nesta fase.
4. Estoque: controlar unidades, entradas, consumo, perdas, contagens e ajustes justificados. A falta de registros deve aparecer como pendência, não como saldo confiável.
5. Produção: separar peso cru e pronto, rendimento, porção servida e sobras. Definir um único método de baixa em cada etapa para não descontar ingredientes duas vezes.
6. Financeiro: separar venda, recebimento, despesa, pagamento, transferência e reembolso. Não contar crédito bancário como uma nova venda já registrada.
7. Reembolso: vincular nota, compra, responsável pelo adiantamento e pagamentos, permitindo acompanhar saldo pendente sem duplicar despesas. Compras já recebidas e pagas pela equipe não devem depender do reembolso para entrar no estoque.
8. Valores: usar Decimal/Numeric ou centavos inteiros para dinheiro, evitando float nos cálculos. Validar quantidades, arredondamentos e transações no backend.
9. Datas: preservar data do acontecimento e data do lançamento. Usar datas e horários consistentes com America/Sao_Paulo. Aceitar registros tardios sem atribuí-los automaticamente ao dia de digitação.
10. Meta: enquanto valor e base não forem definidos, mostrar “meta pendente”. Não assumir meta zero, lucro ou faturamento como base padrão válida. Guardar a regra vigente por período quando ela for informada.
11. Histórico: preservar rastreabilidade de operações financeiras, estoque e trocas de responsabilidade. Correções precisam de histórico e justificativa, sem apagamentos silenciosos.
12. Dados: manter demonstração e testes separados dos registros reais. Não inventar funcionários, vendas ou custos como se fossem reais.

## Roteiro incremental

1. Fundação: backend, frontend, conexão PostgreSQL, migração inicial, tela inicial e instruções de execução.
2. Equipe e caixa: funcionários, escalas, dias fechados e responsável previsto, com confirmação e substituições manuais.
3. Estoque: produtos e insumos, unidades, inventário inicial e histórico de movimentações.
4. Compras: solicitações, recebimento, documentos e reembolsos.
5. Caixa e financeiro: abertura, passagem, fechamento, vendas, despesas, retiradas e conciliação.
6. Produção: ficha técnica, rendimento, marmitas, perdas e consumo da equipe conforme regras levantadas.
7. Relatórios: acompanhamento mensal e remuneração após definição do acordo.
8. Importações: relatórios Stone somente após validar os formatos disponíveis; melhorar backup e testar restauração com dados de teste.

Cada etapa pode ser dividida em tarefas menores se necessário. Testes devem acompanhar as regras implementadas, principalmente dinheiro, estoque, conflitos de escala e duplicidade de lançamentos.

## Comece agora: somente etapa 1

Inspecione os arquivos e o ambiente e apresente um resumo curto do que encontrou. Em seguida, prepare a base mínima funcional: FastAPI com endpoint de saúde, React consumindo a API, configuração do PostgreSQL local, conexão verificável, migração inicial e documentação dos comandos.

Um endpoint que apenas retorna “ok” não comprova conexão com o banco: verifique o PostgreSQL separadamente e mostre falhas de conexão de forma clara. Valide o build do frontend e o funcionamento da API com o banco. Se faltar um pré-requisito que você não conseguir resolver, explique exatamente o que falta, sem afirmar que a etapa foi concluída.

Não implemente nesta etapa estoque, caixa, equipe, autenticação completa, integração Stone ou integração WhatsApp. Entregue uma base pequena que eu consiga executar e entender. Ao finalizar, atualize ESTADO_DO_PROJETO.md e pare nessa etapa.
